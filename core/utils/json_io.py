import json
from pathlib import Path

def write_json_safe(path: Path, data: dict, append: bool = False):
    """Safely write JSON data to the given file. Append newline-delimited if append=True."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if append and path.exists():
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data))
            f.write("\n")
    else:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2) 