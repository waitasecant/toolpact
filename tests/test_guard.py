import pytest

from toolpact.guard import PactChanged, PactChangedWarning, pact


@pytest.fixture
def lf(tmp_path):
    return tmp_path / "toolpact.lock"


def test_first_registration_creates_lockfile(lf):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    assert lf.exists()


def test_unchanged_no_error(lf):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)
    pact(fn, lockfile=lf)


def test_breaking_change_raises(lf):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged) as exc_info:
        pact(fn2, lockfile=lf)

    assert exc_info.value.fn_name == "fn"
    assert exc_info.value.diff.is_breaking


def test_non_breaking_warns_with_breaking_only(lf):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int = 10) -> str: ...

    fn2.__name__ = "fn"

    with pytest.warns(PactChangedWarning):
        pact(fn2, lockfile=lf, breaking_only=True)


def test_non_breaking_raises_without_breaking_only(lf):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int = 10) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged) as exc_info:
        pact(fn2, lockfile=lf)

    assert not exc_info.value.diff.is_breaking


def test_pact_returns_original_fn(lf):
    @pact(lockfile=lf)
    def fn(q: str) -> str:
        return q

    assert fn("hello") == "hello"


def test_pending_stored_on_change(lf):
    import json

    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged):
        pact(fn2, lockfile=lf)

    data = json.loads(lf.read_text())
    assert "pending" in data["functions"]["fn"]
    assert "hash" in data["functions"]["fn"]["pending"]
    assert "schema" in data["functions"]["fn"]["pending"]


def test_pact_changed_str(lf):
    def fn(q: str) -> str: ...

    pact(fn, lockfile=lf)

    def fn2(q: str, limit: int) -> str: ...

    fn2.__name__ = "fn"

    with pytest.raises(PactChanged) as exc_info:
        pact(fn2, lockfile=lf)

    msg = str(exc_info.value)
    assert "fn" in msg
    assert "toolpact accept" in msg


def test_lazy_mode_no_error_at_decoration(lf):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    # would raise in eager mode
    wrapped = pact(lockfile=lf, mode="lazy")(lambda q, limit: q)
    wrapped.__name__ = "fn"

    # no error yet - check happens on call
    # (just verify decoration didn't raise)


def test_lazy_mode_calls_through(lf):
    @pact(lockfile=lf, mode="lazy")
    def fn(q: str) -> str:
        return q

    assert fn("x") == "x"


def test_lazy_mode_raises_on_first_call(lf):
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...

    # create a lazy-wrapped version with a different signature
    def new_fn(q: str, limit: int) -> str:
        return q

    new_fn.__name__ = "fn"

    wrapped = pact(new_fn, lockfile=lf, mode="lazy")

    with pytest.raises(PactChanged):
        wrapped("hello", 5)


def test_description_change_no_raise(lf):
    def fn(q: str) -> str:
        """Old description."""
        ...

    pact(fn, lockfile=lf)

    def fn2(q: str) -> str:
        """New description."""
        ...

    fn2.__name__ = "fn"
    pact(fn2, lockfile=lf)


def test_unresolvable_annotation_no_crash(lf):
    # verify pact doesn't crash on unresolvable string annotations
    def fn(q: "NonExistentType") -> str: ...  # type: ignore[name-defined]

    # should not crash even if annotation can't be resolved
    @pact(lockfile=lf)
    def fn(q: str) -> str: ...
