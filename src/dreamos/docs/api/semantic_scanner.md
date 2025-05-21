# Semantic Scanner API Documentation

## Overview
The semantic scanner provides intelligent code analysis and pattern matching capabilities.

## Core Functions

### `scan_codebase(query: str, target_dirs: List[str]) -> List[Dict]`
Searches codebase for semantically relevant matches.

Parameters:
- `query`: Search query string
- `target_dirs`: List of directories to search

Returns:
- List of matches with file paths and context

### `analyze_pattern(pattern: str, context: Dict) -> Dict`
Analyzes code patterns in given context.

Parameters:
- `pattern`: Pattern to analyze
- `context`: Context dictionary

Returns:
- Analysis results with confidence scores

## Usage Examples

```python
from dreamos.core.scanner import SemanticScanner

scanner = SemanticScanner()
results = scanner.scan_codebase(
    query="error handling patterns",
    target_dirs=["src/dreamos/core"]
)
```

## Error Handling
- Retries automatically on timeout
- Logs errors without stopping
- Returns empty list on failure 