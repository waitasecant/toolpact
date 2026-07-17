from toolpact.diff import compute_diff


def _s(props, required=None):
    return {
        "name": "fn",
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required or [],
        },
    }


def test_no_changes():
    s = _s({"q": {"type": "string"}}, ["q"])
    diff = compute_diff(s, s)
    assert not diff.changes
    assert not diff.is_breaking


def test_param_added_optional():
    old = _s({"q": {"type": "string"}}, ["q"])
    new = _s({"q": {"type": "string"}, "n": {"type": "integer", "default": 5}}, ["q"])
    diff = compute_diff(old, new)
    assert len(diff.changes) == 1
    assert diff.changes[0].kind == "added"
    assert not diff.changes[0].breaking
    assert not diff.is_breaking


def test_param_added_required():
    old = _s({"q": {"type": "string"}}, ["q"])
    new = _s({"q": {"type": "string"}, "n": {"type": "integer"}}, ["q", "n"])
    diff = compute_diff(old, new)
    added = [c for c in diff.changes if c.kind == "added"]
    assert any(c.breaking for c in added)
    assert diff.is_breaking


def test_param_removed():
    old = _s({"q": {"type": "string"}, "n": {"type": "integer"}}, ["q"])
    new = _s({"q": {"type": "string"}}, ["q"])
    diff = compute_diff(old, new)
    assert any(c.kind == "removed" and c.param == "n" for c in diff.changes)
    assert diff.is_breaking


def test_required_param_type_changed():
    old = _s({"q": {"type": "string"}}, ["q"])
    new = _s({"q": {"type": "integer"}}, ["q"])
    diff = compute_diff(old, new)
    assert any(c.kind == "type_changed" and c.breaking for c in diff.changes)


def test_optional_param_type_changed():
    old = _s({"n": {"type": "string", "default": "x"}}, [])
    new = _s({"n": {"type": "integer", "default": 1}}, [])
    diff = compute_diff(old, new)
    tc = [c for c in diff.changes if c.kind == "type_changed"]
    assert tc
    assert not tc[0].breaking


def test_optional_to_required():
    old = _s({"q": {"type": "string"}, "n": {"type": "integer", "default": 5}}, ["q"])
    new = _s({"q": {"type": "string"}, "n": {"type": "integer"}}, ["q", "n"])
    diff = compute_diff(old, new)
    rc = [c for c in diff.changes if c.kind == "required_changed"]
    assert any(c.breaking for c in rc)


def test_required_to_optional():
    old = _s({"q": {"type": "string"}, "n": {"type": "integer"}}, ["q", "n"])
    new = _s({"q": {"type": "string"}, "n": {"type": "integer", "default": 5}}, ["q"])
    diff = compute_diff(old, new)
    rc = [c for c in diff.changes if c.kind == "required_changed"]
    assert any(not c.breaking for c in rc)


def test_enum_narrowed():
    old = _s({"tier": {"type": "string", "enum": ["A", "B", "C"]}}, ["tier"])
    new = _s({"tier": {"type": "string", "enum": ["A", "B"]}}, ["tier"])
    diff = compute_diff(old, new)
    ec = [c for c in diff.changes if c.kind == "enum_changed"]
    assert ec and ec[0].breaking


def test_enum_widened():
    old = _s({"tier": {"type": "string", "enum": ["A", "B"]}}, ["tier"])
    new = _s({"tier": {"type": "string", "enum": ["A", "B", "C"]}}, ["tier"])
    diff = compute_diff(old, new)
    ec = [c for c in diff.changes if c.kind == "enum_changed"]
    assert ec and not ec[0].breaking


def test_description_change_no_structural_diff():
    old = _s({"q": {"type": "string", "description": "old"}}, ["q"])
    new = _s({"q": {"type": "string", "description": "new"}}, ["q"])
    diff = compute_diff(old, new)
    assert not any(c.kind == "type_changed" for c in diff.changes)


def test_summary_breaking():
    old = _s({"q": {"type": "string"}}, ["q"])
    new = _s({}, [])
    diff = compute_diff(old, new)
    assert "breaking" in diff.summary()


def test_is_breaking_property():
    old = _s({"q": {"type": "string"}}, ["q"])
    new = _s({"q": {"type": "integer"}}, ["q"])
    diff = compute_diff(old, new)
    assert diff.is_breaking


def test_pretty_contains_param_name():
    old = _s({"q": {"type": "string"}}, ["q"])
    new = _s({"q": {"type": "integer"}}, ["q"])
    diff = compute_diff(old, new)
    assert "q" in diff.pretty()
