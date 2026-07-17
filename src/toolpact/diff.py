import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Change:
    param: str
    kind: str  # "added", "removed", "type_changed", "required_changed", "enum_changed"
    old: Any
    new: Any
    breaking: bool


@dataclass
class SchemaDiff:
    fn_name: str
    changes: list[Change] = field(default_factory=list)

    @property
    def is_breaking(self) -> bool:
        return any(c.breaking for c in self.changes)

    def summary(self) -> str:
        b = sum(1 for c in self.changes if c.breaking)
        nb = len(self.changes) - b
        parts = []
        if b:
            parts.append(f"{b} breaking")
        if nb:
            parts.append(f"{nb} non-breaking")
        if not parts:
            return "no changes"
        return ", ".join(parts) + " change(s)"

    def pretty(self) -> str:
        lines = []
        for c in self.changes:
            tag = "BREAKING" if c.breaking else "non-breaking"
            if c.kind == "added":
                lines.append(f"  [{tag}]  parameter added: {c.param}")
            elif c.kind == "removed":
                lines.append(f"  [BREAKING]  parameter removed: {c.param}")
            elif c.kind == "type_changed":
                lines.append(f"  [{tag}]  type changed: {c.param}")
                lines.append(f"      {c.old}  ->  {c.new}")
            elif c.kind == "required_changed":
                status = "now required" if c.new else "now optional"
                lines.append(f"  [{tag}]  {c.param} is {status}")
            elif c.kind == "enum_changed":
                lines.append(f"  [{tag}]  enum changed: {c.param}")
                lines.append(f"      was: {c.old}")
                lines.append(f"      now: {c.new}")
        lines.append(f"\n  {self.summary()}")
        return "\n".join(lines)


def compute_diff(old: dict, new: dict) -> SchemaDiff:
    fn_name = new.get("name", "")
    changes = []

    old_props = old.get("parameters", {}).get("properties", {})
    new_props = new.get("parameters", {}).get("properties", {})
    old_req = set(old.get("parameters", {}).get("required", []))
    new_req = set(new.get("parameters", {}).get("required", []))

    for name in old_props:
        if name not in new_props:
            changes.append(Change(name, "removed", old_props[name], None, True))

    for name in new_props:
        if name not in old_props:
            is_req = name in new_req
            changes.append(Change(name, "added", None, new_props[name], is_req))

    for name in old_props:
        if name not in new_props:
            continue

        op = old_props[name]
        np = new_props[name]
        old_enum = op.get("enum")
        new_enum = np.get("enum")

        if old_enum != new_enum:
            removed = [v for v in (old_enum or []) if v not in (new_enum or [])]
            changes.append(
                Change(name, "enum_changed", old_enum, new_enum, len(removed) > 0)
            )
        elif _struct(op) != _struct(np):
            breaking = name in old_req
            changes.append(
                Change(name, "type_changed", _struct(op), _struct(np), breaking)
            )

        old_was_req = name in old_req
        new_is_req = name in new_req
        if old_was_req != new_is_req:
            breaking = not old_was_req and new_is_req
            changes.append(
                Change(name, "required_changed", old_was_req, new_is_req, breaking)
            )

    return SchemaDiff(fn_name, changes)


def _struct(prop: dict) -> str:
    stripped = {k: v for k, v in prop.items() if k not in ("description", "default")}
    return json.dumps(stripped, sort_keys=True)
