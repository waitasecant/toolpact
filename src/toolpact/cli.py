import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .diff import compute_diff
from .lock import LOCKFILE, LockFile


def main():
    parser = argparse.ArgumentParser(prog="toolpact")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("check")
    p.add_argument("--lockfile", default=None)

    p = sub.add_parser("diff")
    p.add_argument("fn", nargs="?")
    p.add_argument("--lockfile", default=None)

    p = sub.add_parser("accept")
    p.add_argument("fn", nargs="?")
    p.add_argument("--all", dest="all", action="store_true")
    p.add_argument("--lockfile", default=None)

    p = sub.add_parser("list")
    p.add_argument("--lockfile", default=None)

    p = sub.add_parser("show")
    p.add_argument("fn")
    p.add_argument("--lockfile", default=None)

    args = parser.parse_args()
    lf = Path(args.lockfile) if getattr(args, "lockfile", None) else LOCKFILE

    if args.cmd == "check":
        _check(lf)
    elif args.cmd == "diff":
        _diff(lf, args.fn)
    elif args.cmd == "accept":
        _accept(lf, args.fn, args.all)
    elif args.cmd == "list":
        _list(lf)
    elif args.cmd == "show":
        _show(lf, args.fn)
    else:
        parser.print_help()


def _check(lf: Path):
    lock = LockFile(lf)
    data = lock.read()
    fns = data.get("functions", {})

    if not fns:
        if not lf.exists():
            print(f"warning: {lf} not found. No functions registered.")
        else:
            print("toolpact: no functions registered")
        sys.exit(0)

    changed = []
    print(f"toolpact: checking {len(fns)} function(s) against {lf}\n")

    for name, entry in fns.items():
        if entry.get("pending"):
            p = entry["pending"]
            label = "BREAKING" if p["breaking"] else "non-breaking"
            print(f"  x  {name:<20} SCHEMA CHANGED ({label})")
            changed.append(name)
        else:
            print(f"  v  {name:<20} unchanged")

    if changed:
        print(
            f"\n{len(changed)} function(s) have schema changes. Run 'toolpact diff' to review."
        )
        sys.exit(1)

    print("\nAll schemas match.")
    sys.exit(0)


def _diff(lf: Path, fn_name: str | None):
    lock = LockFile(lf)
    data = lock.read()
    fns = data.get("functions", {})

    targets = {fn_name: fns[fn_name]} if fn_name and fn_name in fns else fns

    found = False
    for name, entry in targets.items():
        if not entry.get("pending"):
            continue
        found = True
        diff = compute_diff(entry["schema"], entry["pending"]["schema"])
        print(f"\n{name}")
        print("-" * 40)
        print(diff.pretty())
        print(f"\n  Run 'toolpact accept {name}' to accept.")

    if not found:
        msg = (
            f"No pending changes for '{fn_name}'." if fn_name else "No pending changes."
        )
        print(msg)


def _accept(lf: Path, fn_name: str | None, accept_all: bool):
    if not fn_name and not accept_all:
        print("Usage: toolpact accept <fn_name> | --all")
        sys.exit(1)

    lock = LockFile(lf)
    data = lock.read()
    fns = data.get("functions", {})

    if accept_all:
        targets: list[str] = list(fns.keys())
    else:
        targets = [fn_name] if fn_name else []

    for name in targets:
        entry = fns.get(name)
        if not entry:
            print(f"  not found: {name}")
            continue
        if not entry.get("pending"):
            print(f"  no pending change: {name}")
            continue

        pending = entry.pop("pending")
        entry["hash"] = pending["hash"]
        entry["schema"] = pending["schema"]
        entry["breaking"] = pending["breaking"]
        entry["accepted_at"] = datetime.now(timezone.utc).isoformat()
        lock.set(name, entry)
        print(f"  accepted: {name}")


def _list(lf: Path):
    lock = LockFile(lf)
    data = lock.read()
    fns = data.get("functions", {})

    if not fns:
        print("No functions registered.")
        return

    header = f"{'Function':<20} {'Hash':<20} {'Accepted at':<26} {'Breaking'}"
    print(header)
    print("-" * len(header))

    for name, entry in fns.items():
        h = entry.get("hash", "")[:20]
        ts = entry.get("accepted_at", "")[:19].replace("T", " ")
        breaking = "yes" if entry.get("breaking") else "no"
        pending = " (pending)" if entry.get("pending") else ""
        print(f"{name:<20} {h:<20} {ts:<26} {breaking}{pending}")


def _show(lf: Path, fn_name: str):
    lock = LockFile(lf)
    entry = lock.get(fn_name)
    if not entry:
        print(f"Function '{fn_name}' not found in lockfile.")
        sys.exit(1)
    print(json.dumps(entry.get("schema", {}), indent=2))
