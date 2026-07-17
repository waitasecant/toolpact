from toolpact.hash import schema_hash


def _s(props, required=None):
    return {
        "name": "fn",
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required or [],
        },
    }


def test_same_schema_same_hash():
    s = _s({"q": {"type": "string"}}, ["q"])
    assert schema_hash(s) == schema_hash(s)


def test_description_ignored():
    s1 = _s({"q": {"type": "string", "description": "old"}}, ["q"])
    s2 = _s({"q": {"type": "string", "description": "new"}}, ["q"])
    assert schema_hash(s1) == schema_hash(s2)


def test_fn_description_ignored():
    s1 = {**_s({"q": {"type": "string"}}, ["q"]), "description": "old"}
    s2 = {**_s({"q": {"type": "string"}}, ["q"]), "description": "new"}
    assert schema_hash(s1) == schema_hash(s2)


def test_type_change_different_hash():
    s1 = _s({"q": {"type": "string"}}, ["q"])
    s2 = _s({"q": {"type": "integer"}}, ["q"])
    assert schema_hash(s1) != schema_hash(s2)


def test_added_param_different_hash():
    s1 = _s({"q": {"type": "string"}}, ["q"])
    s2 = _s({"q": {"type": "string"}, "n": {"type": "integer", "default": 5}}, ["q"])
    assert schema_hash(s1) != schema_hash(s2)


def test_hash_format():
    s = _s({}, [])
    h = schema_hash(s)
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 16


def test_dict_order_independent():
    s1 = {
        "name": "fn",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
            "required": ["a"],
        },
    }
    s2 = {
        "parameters": {
            "required": ["a"],
            "properties": {"b": {"type": "integer"}, "a": {"type": "string"}},
            "type": "object",
        },
        "name": "fn",
    }
    assert schema_hash(s1) == schema_hash(s2)
