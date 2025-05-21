# Semantic Scanner API Documentation

## Overview
The Semantic Scanner provides enhanced code search capabilities through semantic analysis, including code structure analysis, dependency tracking, and semantic indexing.

## Core Classes

### SemanticScanner
Main class for semantic code analysis and search.

#### Initialization
```python
scanner = SemanticScanner(config: AppConfig)
```

#### Methods

##### scan(project_path: Path) -> Dict[str, Any]
Scans a project for semantic information.
- **Parameters:**
  - `project_path`: Path to the project directory
- **Returns:** Dictionary containing semantic information and index

##### search(query: str, project_path: Optional[Path] = None) -> List[Dict[str, Any]]
Searches code using semantic capabilities.
- **Parameters:**
  - `query`: Search query string
  - `project_path`: Optional path to project directory
- **Returns:** List of search results

##### analyze(code_path: Path) -> Dict[str, Any]
Analyzes code for semantic information.
- **Parameters:**
  - `code_path`: Path to code file or directory
- **Returns:** Dictionary containing semantic, structure, and dependency information

## Usage Examples

### Basic Scanning
```python
from dreamos.tools.scanner.semantic_scanner import SemanticScanner
from dreamos.core.config import AppConfig

config = AppConfig()
scanner = SemanticScanner(config)

# Scan project
results = await scanner.scan(Path("my_project"))
```

### Semantic Search
```python
# Search code
results = await scanner.search("class User")
```

### Code Analysis
```python
# Analyze specific file
analysis = await scanner.analyze(Path("my_file.py"))
```

## Output Format

### Scan Results
```python
{
    "semantic_info": {
        "files": {
            "path/to/file.py": {
                "imports": ["module1", "module2"],
                "classes": {
                    "ClassName": {
                        "bases": ["BaseClass"],
                        "docstring": "...",
                        "methods": {...},
                        "decorators": [...]
                    }
                },
                "functions": {...},
                "variables": {...}
            }
        }
    },
    "semantic_index": {...}
}
```

### Search Results
```python
[
    {
        "file": "path/to/file.py",
        "line": 42,
        "context": "...",
        "score": 0.95
    }
]
```

### Analysis Results
```python
{
    "semantic_info": {...},
    "structure_info": {
        "complexity": 10,
        "depth": 3,
        "branches": [...]
    },
    "dependency_info": {
        "imports": [...],
        "calls": [...],
        "inheritance": [...]
    }
}
```

## Features
- AST-based code analysis
- Semantic indexing
- Dependency tracking
- Code structure analysis
- Type inference
- Complexity calculation 