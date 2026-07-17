import json
from pathlib import Path

LOCKFILE = Path("toolpact.lock")


class LockFile:
    def __init__(self, path: Path = LOCKFILE):
        self.path = Path(path)

    def read(self) -> dict:
        if not self.path.exists():
            return {"_toolpact": "1", "functions": {}}
        return json.loads(self.path.read_text())

    def write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def get(self, name: str) -> dict | None:
        return self.read()["functions"].get(name)

    def set(self, name: str, entry: dict) -> None:
        data = self.read()
        data["functions"][name] = entry
        self.write(data)
