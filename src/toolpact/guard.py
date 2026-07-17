import warnings
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar, overload

from .diff import compute_diff
from .hash import schema_hash
from .lock import LOCKFILE, LockFile
from .schema import generate_schema

F = TypeVar("F", bound=Callable[..., Any])


class PactChanged(Exception):
    def __init__(self, fn_name: str, diff):
        self.fn_name = fn_name
        self.diff = diff

    def __str__(self):
        return (
            f"\n[toolpact] Schema changed for '{self.fn_name}'\n"
            f"{self.diff.pretty()}\n\n"
            f"To accept: toolpact accept {self.fn_name}\n"
            f"Accept all: toolpact accept --all\n"
        )


class PactChangedWarning(UserWarning):
    pass


@overload
def pact(
    fn: F, *, breaking_only: bool = ..., lockfile: Path = ..., mode: str = ...
) -> F: ...
@overload
def pact(
    fn: None = ..., *, breaking_only: bool = ..., lockfile: Path = ..., mode: str = ...
) -> Callable[[F], F]: ...
def pact(
    fn=None,
    *,
    breaking_only: bool = False,
    lockfile: Path = LOCKFILE,
    mode: str = "eager",
):
    """
    Decorator that checks a function's tool schema against the lockfile at import time.

    Args:
        breaking_only: only raise on breaking changes, warn on non-breaking ones.
        lockfile: path to the lockfile.
        mode: "eager" (check at import) or "lazy" (check on first call).
    """
    if fn is None:
        return lambda f: pact(
            f, breaking_only=breaking_only, lockfile=lockfile, mode=mode
        )

    if mode == "lazy":
        return _lazy_wrap(fn, breaking_only, lockfile)

    _check(fn, breaking_only, lockfile)
    return fn


def _check(fn, breaking_only, lockfile):
    schema = generate_schema(fn)
    h = schema_hash(schema)
    lock = LockFile(lockfile)
    stored = lock.get(fn.__name__)

    if stored is None:
        lock.set(
            fn.__name__,
            {
                "accepted_at": datetime.now(timezone.utc).isoformat(),
                "breaking": False,
                "hash": h,
                "schema": schema,
            },
        )
        return

    if stored["hash"] == h:
        return

    diff = compute_diff(stored["schema"], schema)

    # store pending change so CLI can read it without importing user code
    entry = dict(stored)
    entry["pending"] = {
        "breaking": diff.is_breaking,
        "hash": h,
        "schema": schema,
    }
    lock.set(fn.__name__, entry)

    if breaking_only and not diff.is_breaking:
        warnings.warn(
            f"[toolpact] {fn.__name__}: non-breaking schema change.\n{diff.summary()}",
            PactChangedWarning,
            stacklevel=4,
        )
        return

    raise PactChanged(fn.__name__, diff)


def _lazy_wrap(fn, breaking_only, lockfile):
    checked = False

    def wrapper(*args, **kwargs):
        nonlocal checked
        if not checked:
            _check(fn, breaking_only, lockfile)
            checked = True
        return fn(*args, **kwargs)

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__annotations__ = fn.__annotations__
    return wrapper
