import json
import sys

import pytest

from toolpact.guard import PactChanged, pact
from toolpact.lock import LockFile


@pytest.fixture
def lf(tmp_path):
    return tmp_path / "toolpact.lock"


def run(args, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["toolpact"] + args)
    try:
        from toolpact.cli import main

        main()
        return 0
    except SystemExit as e:
        return e.code


def test_check_no_changes(lf, monkeypatch, capsys):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    assert code == 0
    assert "unchanged" in capsys.readouterr().out


def test_check_with_pending(lf, monkeypatch, capsys):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged):
        pact(fn2, lockfile=lf)

    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    assert code == 1
    assert "SCHEMA CHANGED" in capsys.readouterr().out


def test_check_missing_lockfile(lf, monkeypatch, capsys):
    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    assert code == 0
    assert "warning" in capsys.readouterr().out.lower()


def test_diff_shows_changes(lf, monkeypatch, capsys):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged):
        pact(fn2, lockfile=lf)

    run(["diff", "--lockfile", str(lf)], monkeypatch)
    out = capsys.readouterr().out
    assert "fn" in out
    assert "limit" in out


def test_diff_no_changes(lf, monkeypatch, capsys):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    run(["diff", "--lockfile", str(lf)], monkeypatch)
    assert "No pending" in capsys.readouterr().out


def test_accept_fn(lf, monkeypatch, capsys):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged):
        pact(fn2, lockfile=lf)

    run(["accept", "fn", "--lockfile", str(lf)], monkeypatch)

    data = json.loads(lf.read_text())
    entry = data["functions"]["fn"]
    assert "pending" not in entry
    assert "limit" in entry["schema"]["parameters"]["properties"]
    assert "accepted" in capsys.readouterr().out


def test_accept_all(lf, monkeypatch):
    def fn1(q: str) -> str: ...

    pact(fn1, lockfile=lf)

    def fn2(x: int) -> int: ...

    pact(fn2, lockfile=lf)

    def fn1_new(q: str, limit: int) -> str: ...

    fn1_new.__name__ = "fn1"

    def fn2_new(x: int, y: int) -> int: ...

    fn2_new.__name__ = "fn2"

    with pytest.raises(PactChanged):
        pact(fn1_new, lockfile=lf)

    with pytest.raises(PactChanged):
        pact(fn2_new, lockfile=lf)

    run(["accept", "--all", "--lockfile", str(lf)], monkeypatch)

    data = json.loads(lf.read_text())
    assert "pending" not in data["functions"]["fn1"]
    assert "pending" not in data["functions"]["fn2"]


def test_accept_no_args_exits_1(lf, monkeypatch):
    code = run(["accept", "--lockfile", str(lf)], monkeypatch)
    assert code == 1


def test_list(lf, monkeypatch, capsys):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    run(["list", "--lockfile", str(lf)], monkeypatch)
    out = capsys.readouterr().out
    assert "fn" in out


def test_list_pending_label(lf, monkeypatch, capsys):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged):
        pact(fn2, lockfile=lf)

    run(["list", "--lockfile", str(lf)], monkeypatch)
    assert "pending" in capsys.readouterr().out


def test_show(lf, monkeypatch, capsys):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    run(["show", "fn", "--lockfile", str(lf)], monkeypatch)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "fn"


def test_show_not_found(lf, monkeypatch, capsys):
    lock = LockFile(lf)
    lock.set("fn", {"hash": "x", "schema": {}})

    code = run(["show", "missing", "--lockfile", str(lf)], monkeypatch)
    assert code == 1


def test_full_workflow(lf, monkeypatch, capsys):
    def search(query: str, max_results: int = 10) -> list[str]: ...

    pact(search, lockfile=lf)

    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    capsys.readouterr()
    assert code == 0

    def search_v2(query: str, max_results: int = 10, offset: int = 0) -> list[str]: ...

    search_v2.__name__ = "search"

    with pytest.raises(PactChanged):
        pact(search_v2, lockfile=lf)

    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    capsys.readouterr()
    assert code == 1

    run(["accept", "search", "--lockfile", str(lf)], monkeypatch)
    capsys.readouterr()

    # re-register accepted schema (simulate restart)
    pact(search_v2, lockfile=lf)

    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    capsys.readouterr()
    assert code == 0


def test_no_subcommand(monkeypatch, capsys):
    code = run([], monkeypatch)
    assert code == 0


def test_check_empty_lockfile(lf, monkeypatch, capsys):
    LockFile(lf).write({"_toolpact": "1", "functions": {}})
    code = run(["check", "--lockfile", str(lf)], monkeypatch)
    assert code == 0
    assert "no functions registered" in capsys.readouterr().out


def test_diff_fn_no_changes(lf, monkeypatch, capsys):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)
    run(["diff", "fn", "--lockfile", str(lf)], monkeypatch)
    assert "No pending changes for 'fn'" in capsys.readouterr().out


def test_accept_no_pending(lf, monkeypatch, capsys):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)
    run(["accept", "fn", "--lockfile", str(lf)], monkeypatch)
    assert "no pending change" in capsys.readouterr().out


def test_list_empty(lf, monkeypatch, capsys):
    run(["list", "--lockfile", str(lf)], monkeypatch)
    assert "No functions registered" in capsys.readouterr().out


def test_accept_not_found(lf, monkeypatch, capsys):
    run(["accept", "missing", "--lockfile", str(lf)], monkeypatch)
    assert "not found" in capsys.readouterr().out
