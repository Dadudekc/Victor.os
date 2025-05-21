# Semantic Search Tool

A powerful semantic search tool that combines transformer-based semantic matching with fuzzy string matching for improved search results.

## Features

- Semantic search using Sentence Transformers
- Fuzzy string matching for partial matches
- Combined scoring system (60% semantic, 40% fuzzy)
- CLI interface for easy usage
- Support for multiple file types (.py, .md, .txt)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Search in current directory
python -m dreamos.tools.search.cli semantic-search "your query"

# Search in specific directory
python -m dreamos.tools.search.cli semantic-search "your query" --directory /path/to/dir

# Get more results
python -m dreamos.tools.search.cli semantic-search "your query" --top-k 10
```

### Python API

```python
from dreamos.tools.search import SemanticFuzzySearcher

# Initialize with documents
searcher = SemanticFuzzySearcher(documents)

# Search
results = searcher.search("your query", top_k=5)
```

## Dependencies

- sentence-transformers
- rapidfuzz
- torch
- click (for CLI)

## Performance

The tool uses the lightweight "all-MiniLM-L6-v2" model for semantic search, providing a good balance between performance and accuracy. Fuzzy matching helps catch partial matches and typos. 