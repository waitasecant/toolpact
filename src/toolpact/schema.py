import inspect
import re
import types as _types
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints


def generate_schema(fn) -> dict:
    try:
        hints = get_type_hints(fn, include_extras=False)
    except Exception:
        hints = {}

    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""
    props = {}
    required = []

    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        ann = hints.get(name, Any)
        prop = _to_schema(ann)

        desc = _param_doc(doc, name)
        if desc:
            prop["description"] = desc

        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            if param.default is not None:
                prop["default"] = param.default

        props[name] = prop

    return {
        "name": fn.__name__,
        "description": doc.split("\n\n")[0] if doc else "",
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required,
        },
    }


def _to_schema(ann) -> dict:
    if ann is Any or ann is inspect.Parameter.empty:
        return {}

    # handle Python 3.10+ X | Y syntax
    if hasattr(_types, "UnionType") and isinstance(ann, _types.UnionType):
        ann = Union[get_args(ann)]

    origin = get_origin(ann)
    args = get_args(ann)

    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        has_none = type(None) in args

        if has_none and len(non_none) == 1:
            inner = _to_schema(non_none[0])
            t = inner.get("type")
            if t and isinstance(t, str):
                return {**inner, "type": [t, "null"]}
            return {"anyOf": [inner, {"type": "null"}]}

        return {"anyOf": [_to_schema(a) for a in args]}

    if origin is list:
        return {"type": "array", "items": _to_schema(args[0]) if args else {}}

    if origin is dict:
        return {"type": "object"}

    if origin is Literal:
        vals = list(args)
        if all(isinstance(v, str) for v in vals):
            return {"type": "string", "enum": vals}
        if all(isinstance(v, int) for v in vals):
            return {"type": "integer", "enum": vals}
        return {"enum": vals}

    _map = {str: "string", int: "integer", float: "number", bool: "boolean"}
    if ann in _map:
        return {"type": _map[ann]}

    return {}


def _param_doc(doc: str, name: str) -> str:
    # Google style: "    name (type): description"
    m = re.search(
        rf"^\s+{re.escape(name)}\s*(?:\([^)]*\))?\s*:\s*(.+)$", doc, re.MULTILINE
    )
    if m:
        return m.group(1).strip()

    # NumPy style: "name : type\n    description"
    m = re.search(rf"^\s*{re.escape(name)}\s*:.*\n\s+(.+)$", doc, re.MULTILINE)
    if m:
        return m.group(1).strip()

    return ""
