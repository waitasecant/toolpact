from typing import Any, Literal, Optional, Union

from toolpact.schema import _to_schema, generate_schema


def test_str():
    assert _to_schema(str) == {"type": "string"}


def test_int():
    assert _to_schema(int) == {"type": "integer"}


def test_float():
    assert _to_schema(float) == {"type": "number"}


def test_bool():
    assert _to_schema(bool) == {"type": "boolean"}


def test_list_str():
    assert _to_schema(list[str]) == {"type": "array", "items": {"type": "string"}}


def test_dict():
    assert _to_schema(dict[str, Any]) == {"type": "object"}


def test_literal_str():
    assert _to_schema(Literal["a", "b"]) == {"type": "string", "enum": ["a", "b"]}


def test_literal_int():
    assert _to_schema(Literal[1, 2]) == {"type": "integer", "enum": [1, 2]}


def test_optional():
    assert _to_schema(Optional[str]) == {"type": ["string", "null"]}


def test_union_with_none_pipe():
    assert _to_schema(str | None) == {"type": ["string", "null"]}


def test_union():
    assert _to_schema(Union[str, int]) == {"anyOf": [{"type": "string"}, {"type": "integer"}]}


def test_any():
    assert _to_schema(Any) == {}


def test_generate_basic():
    def search(query: str, max_results: int = 10) -> list[str]:
        """Search documents."""
        ...

    s = generate_schema(search)
    assert s["name"] == "search"
    assert s["description"] == "Search documents."
    assert "query" in s["parameters"]["properties"]
    assert "max_results" in s["parameters"]["properties"]
    assert s["parameters"]["required"] == ["query"]
    assert s["parameters"]["properties"]["max_results"]["default"] == 10


def test_generate_no_annotations():
    def legacy(query, limit):
        ...

    s = generate_schema(legacy)
    assert s["parameters"]["properties"]["query"] == {}
    assert s["parameters"]["properties"]["limit"] == {}
    assert set(s["parameters"]["required"]) == {"query", "limit"}


def test_generate_skips_args_kwargs():
    def fn(*args, **kwargs):
        ...

    s = generate_schema(fn)
    assert s["parameters"]["properties"] == {}


def test_generate_google_docstring():
    def fn(query: str):
        """Do something.

        Args:
            query (str): The search query.
        """
        ...

    s = generate_schema(fn)
    assert s["parameters"]["properties"]["query"]["description"] == "The search query."


def test_generate_numpy_docstring():
    def fn(query: str):
        """Do something.

        Parameters
        ----------
        query : str
            The search query.
        """
        ...

    s = generate_schema(fn)
    assert s["parameters"]["properties"]["query"]["description"] == "The search query."


def test_none_default_not_stored():
    def fn(limit: int | None = None):
        ...

    s = generate_schema(fn)
    assert "default" not in s["parameters"]["properties"]["limit"]


def test_first_paragraph_description():
    def fn(q: str):
        """Short desc.

        More details here.
        """
        ...

    s = generate_schema(fn)
    assert s["description"] == "Short desc."
