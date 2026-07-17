import pytest

from toolpact.lock import LockFile


@pytest.fixture
def lock(tmp_path):
    return LockFile(tmp_path / "toolpact.lock")


def test_read_missing(lock):
    assert lock.read() == {"_toolpact": "1", "functions": {}}


def test_roundtrip(lock):
    entry = {"hash": "sha256:abc", "schema": {"name": "fn"}, "accepted_at": "2026-01-01", "breaking": False}
    lock.set("fn", entry)
    assert lock.get("fn") == entry


def test_get_missing(lock):
    assert lock.get("nonexistent") is None


def test_multiple_functions(lock):
    lock.set("fn1", {"hash": "a"})
    lock.set("fn2", {"hash": "b"})
    assert lock.get("fn1") == {"hash": "a"}
    assert lock.get("fn2") == {"hash": "b"}


def test_overwrite(lock):
    lock.set("fn", {"hash": "old"})
    lock.set("fn", {"hash": "new"})
    assert lock.get("fn") == {"hash": "new"}


def test_file_ends_with_newline(lock):
    lock.set("fn", {"hash": "x"})
    assert lock.path.read_text().endswith("\n")
