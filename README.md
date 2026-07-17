# `toolpact`

[![PyPI Version](https://img.shields.io/pypi/v/toolpact?pypiBaseUrl=https%3A%2F%2Fpypi.org&logo=pypi&logoColor=white&label=PyPI&color=neongreen)](https://pypi.org/project/toolpact/)
[![Tests](https://img.shields.io/github/actions/workflow/status/waitasecant/toolpact/test.yml?logo=github&label=Tests)](https://github.com/waitasecant/toolpact/actions/workflows/test.yml)
[![Codecov](https://img.shields.io/codecov/c/github/waitasecant/toolpact?logo=codecov&label=Coverage&color=neongreen)](https://codecov.io/gh/waitasecant/toolpact)
[![License: MIT](https://img.shields.io/badge/License-MIT-neon.svg)](LICENSE)

*Catch breaking signature changes before they reach a deployed agent. `package-lock.json` for LLM tool schemas.*

## Why `toolpact`?

Tool schemas are generated from Python function signatures at runtime. When you rename a parameter, the schema silently changes. LLMs in deployed sessions were prompted with the old schema — they keep sending tool calls with the old argument names until they fail. No linter catches this. No type checker catches this. It is invisible.

`toolpact` treats the schema as a versioned contract. First run — generates the schema, hashes it, writes `toolpact.lock`. Every subsequent run — regenerates and compares. If the schema changed, it raises `PactChanged` and blocks startup until you explicitly accept the change.

---

## How it works

### Check at decoration time, not call time
The `@pact` decorator runs when Python loads the module — at import, before any request is served. A schema change crashes the import, not a live call. The wrapped function is returned unchanged, so there is zero per-call overhead.

### Hash of canonical JSON Schema.
The schema is serialized with sorted keys and no whitespace before hashing. Identical schemas always produce the same hash regardless of dict insertion order. Description fields are stripped before hashing — changing a docstring never triggers a check, only structural changes do (parameter names, types, required status).

### Lockfile in version control
`toolpact.lock` is committed to git. A signature change produces a diff in the lockfile that is visible in PR review. Reviewers see exactly what the LLM contract changed before it merges.

### Breaking vs non-breaking
Adding an optional parameter is non-breaking — LLMs using the old schema still work, they just won't use the new argument. Renaming a required parameter is breaking — the LLM sends the old name and the function fails. `toolpact` classifies every change so you can decide how to respond.

---

## Installation

```bash
pip install toolpact
```

---

## Quick Start

### Step 1: Decorate your tools

```python
from toolpact import pact

@pact
def search(query: str, max_results: int = 10) -> list[str]:
    """Search documents by query."""
    ...

@pact
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city."""
    ...
```

First import: both functions are registered in `toolpact.lock`. Commit this file.

### Step 2: Change a signature

```python
# renamed: query -> search_query
@pact
def search(search_query: str, max_results: int = 10) -> list[str]:
    """Search documents by query."""
    ...
```

Next import raises immediately:

```
[toolpact] Schema changed for 'search'

  [BREAKING]  parameter removed: query
  [BREAKING]  parameter added: search_query

  2 breaking change(s).

To accept: toolpact accept search
Accept all: toolpact accept --all
```

### Step 3: Review and accept

```bash
toolpact diff            # show all pending changes
toolpact accept search   # accept and update lockfile
```

Re-import — no error.

---

## CI Integration

Add to your pipeline to block merges that silently break tool contracts:

```yaml
# .github/workflows/ci.yml
- name: Check tool schema contracts
  run: toolpact check
```

`toolpact check` exits 0 if all schemas match, exits 1 if any have pending changes:

```
toolpact: checking 3 function(s) against toolpact.lock

  v  get_weather          unchanged
  v  summarize            unchanged
  x  search               SCHEMA CHANGED (BREAKING)

1 function(s) have schema changes. Run 'toolpact diff' to review.
```

---

## Change Classification

Not every signature change breaks a deployed agent. `toolpact` classifies each:

| Change | Breaking? | Reason |
|---|---|---|
| Required parameter renamed | Yes | LLM sends old name, function expects new name |
| Required parameter removed | Yes | LLM sends it, function no longer accepts it |
| Required parameter type changed | Yes | LLM sends old type, function expects new type |
| Optional parameter removed | Yes | LLM might send it if prompted with old schema |
| Parameter made required (was optional) | Yes | LLM with old schema won't send it |
| Enum narrowed (values removed) | Yes | LLM might send a removed value |
| Optional parameter added | No | LLM won't send it — default covers it |
| Parameter made optional (was required) | No | LLM still sends it, function still works |
| Enum widened (values added) | No | Old values remain valid |
| Description changed | No | Excluded from hash — docstring edits never trigger a check |

Use `breaking_only=True` to warn instead of raise on non-breaking changes:

```python
@pact(breaking_only=True)
def search(query: str, max_results: int = 10, offset: int = 0) -> list[str]:
    ...
```

---

## CLI Reference

```bash
toolpact check                  # exit 0 if all match, exit 1 if any changed
toolpact diff                   # show diff for all pending changes
toolpact diff <fn_name>         # show diff for one function
toolpact accept <fn_name>       # accept change, update lockfile
toolpact accept --all           # accept all pending changes
toolpact list                   # list all registered functions with timestamps
toolpact show <fn_name>         # print current stored schema as JSON
```

---

## Lockfile Format

`toolpact.lock` is plain JSON — commit it, never ignore it:

```json
{
  "_toolpact": "1",
  "functions": {
    "search": {
      "accepted_at": "2026-07-12T10:00:00Z",
      "breaking": false,
      "hash": "sha256:a3f9b2c1d4e5f678",
      "schema": {
        "name": "search",
        "description": "Search documents by query.",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 10}
          },
          "required": ["query"]
        }
      }
    }
  }
}
```

A signature change produces a visible diff in this file — reviewers see exactly what the LLM contract changed before the PR merges.

---

## Options

```python
@pact(
    breaking_only=False,       # warn on non-breaking, raise only on breaking
    lockfile="toolpact.lock",  # custom lockfile path
    mode="eager",              # "eager": check at import | "lazy": check on first call
)
def my_tool(...): ...
```

`mode="lazy"` is useful in notebooks and scripts where import-time failures are inconvenient. `mode="eager"` (default) is safer for production servers — fail fast before any request is served.
