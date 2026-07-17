import hashlib
import json


def schema_hash(schema: dict) -> str:
    stripped = _strip(schema)
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return f"sha256:{digest}"


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k != "description"}
    if isinstance(obj, list):
        return [_strip(i) for i in obj]
    return obj
