# File I/O Utilities (`src/dreamos/utils/file_io.py`)

This module provides robust and standardized functions for common file
input/output operations, particularly focusing on JSON, JSON Lines (JSONL), and
text files. It includes atomic writes to prevent data corruption from incomplete
operations.

## Core Concepts

- **Atomic Writes:** Functions like `write_json_atomic` and
  `write_text_file_atomic` use a temporary file mechanism. They write the
  complete content to a temporary file first, then atomically replace the target
  file with the temporary file. This ensures that the target file is always in a
  consistent state, even if the write process is interrupted.
- **Error Handling:** Functions generally return `None` or an empty list (`[]`)
  on failure (e.g., file not found, permission denied, decoding errors) and log
  detailed errors. Write functions may raise `FileIOError` (a custom exception
  inheriting from `IOError`) on failure.
- **Path Handling:** Functions accept both string paths and `pathlib.Path`
  objects.
- **Directory Creation:** Write/append functions automatically create necessary
  parent directories if they don't exist using
  `path.parent.mkdir(parents=True, exist_ok=True)`.

## JSON Utilities

### `read_json_file(path: Union[str, Path]) -> Optional[Union[Dict, List]]`

Reads a standard JSON file.

- **Args:**
  - `path`: Path to the JSON file.
- **Returns:** A dictionary or list representing the parsed JSON content, or
  `None` if the file doesn't exist, is empty, cannot be decoded, or another I/O
  error occurs.

```python
from dreamos.utils.file_io import read_json_file

data = read_json_file("runtime/config.json")
if data:
    print("Config loaded:", data)
else:
    print("Failed to load config.json")
```

### `write_json_atomic(path: Union[str, Path], data: Union[Dict, List], indent: Optional[int] = 2)`

Atomically writes a Python dictionary or list to a JSON file.

- **Args:**
  - `path`: Path to the target JSON file.
  - `data`: The dictionary or list to write.
  - `indent` (Optional[int]): JSON indentation level (default: 2). Use `None`
    for a compact representation.
- **Behavior:** Writes to a temporary file first, then replaces the original
  file.
- **Raises:** `FileIOError` on failure.

```python
from dreamos.utils.file_io import write_json_atomic, FileIOError

my_data = {"agent_id": "A01", "status": "active"}
try:
    write_json_atomic("runtime/agent_status.json", my_data)
    print("Agent status saved.")
except FileIOError as e:
    print(f"Error saving agent status: {e}")
```

## JSON Lines (JSONL) Utilities

JSONL is a format where each line is a valid, independent JSON object.

### `append_jsonl(path: Union[str, Path], data: Dict)`

Appends a dictionary as a new line to a JSONL file.

- **Args:**
  - `path`: Path to the JSONL file.
  - `data`: The dictionary to append.
- **Behavior:** Opens the file in append mode (`'a'`), writes the
  JSON-serialized dictionary followed by a newline.
- **Raises:** `FileIOError` on failure.

```python
from dreamos.utils.file_io import append_jsonl, FileIOError

log_entry = {"timestamp": "...", "event": "TASK_START", "agent": "A02"}
try:
    append_jsonl("runtime/logs/events.jsonl", log_entry)
except FileIOError as e:
    print(f"Failed to log event: {e}")
```

### `read_jsonl_file(path: Union[str, Path]) -> List[Dict]`

Reads a JSONL file line by line.

- **Args:**
  - `path`: Path to the JSONL file.
- **Returns:** A list of dictionaries, where each dictionary corresponds to a
  successfully parsed line. Invalid JSON lines are skipped, and an error is
  logged.

```python
from dreamos.utils.file_io import read_jsonl_file

all_events = read_jsonl_file("runtime/logs/events.jsonl")
print(f"Loaded {len(all_events)} events.")
```

## Text File Utilities

### `read_text_file(path: Union[str, Path], encoding: str = 'utf-8') -> Optional[str]`

Reads an entire text file.

- **Args:**
  - `path`: Path to the text file.
  - `encoding` (str): File encoding (default: 'utf-8').
- **Returns:** The content of the file as a string, or `None` on error.

```python
from dreamos.utils.file_io import read_text_file

readme_content = read_text_file("README.md")
if readme_content:
    print("README loaded.")
```

### `write_text_file_atomic(path: Union[str, Path], content: str, encoding: str = 'utf-8')`

Atomically writes string content to a text file.

- **Args:**
  - `path`: Path to the target text file.
  - `content` (str): The string content to write.
  - `encoding` (str): File encoding (default: 'utf-8').
- **Behavior:** Writes to a temporary file first, then replaces the original
  file.
- **Raises:** `FileIOError` on failure.

```python
from dreamos.utils.file_io import write_text_file_atomic, FileIOError

report = "Analysis complete.\nErrors found: 0"
try:
    write_text_file_atomic("runtime/reports/analysis_summary.txt", report)
    print("Report saved.")
except FileIOError as e:
    print(f"Error saving report: {e}")
```

## Directory Utilities

### `ensure_directory_exists(path: Union[str, Path])`

Ensures that the _parent directory_ of the given path exists, creating it if
necessary.

- **Args:**
  - `path`: The full path (including filename) for which the parent directory
    needs to exist.
- **Behavior:** Calls `Path(path).parent.mkdir(parents=True, exist_ok=True)`.

```python
from dreamos.utils.file_io import ensure_directory_exists

# Before writing to "runtime/logs/special/report.txt":
ensure_directory_exists("runtime/logs/special/report.txt")
# Now the "runtime/logs/special/" directory is guaranteed to exist.
```

## Error Handling

### `FileIOError`

A custom exception class inheriting from `IOError`. Raised by write/append
functions on failure to indicate an error specifically from this module's
operations.
