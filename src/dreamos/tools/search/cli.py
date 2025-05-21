import click
import logging
from typing import List
from pathlib import Path
from .semantic_search import SemanticFuzzySearcher

logger = logging.getLogger(__name__)

def load_documents(directory: str) -> List[str]:
    """Load documents from directory."""
    docs = []
    for path in Path(directory).rglob("*"):
        if path.is_file() and path.suffix in ['.py', '.md', '.txt']:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    docs.append(f.read())
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")
    return docs

@click.group()
def search():
    """Semantic search CLI."""
    pass

@search.command()
@click.argument('query')
@click.option('--directory', '-d', default='.', help='Directory to search in')
@click.option('--top-k', '-k', default=5, help='Number of results to return')
def semantic_search(query: str, directory: str, top_k: int):
    """Search documents using semantic and fuzzy matching."""
    try:
        docs = load_documents(directory)
        if not docs:
            click.echo("No documents found in directory")
            return
            
        searcher = SemanticFuzzySearcher(docs)
        results = searcher.search(query, top_k=top_k)
        
        click.echo(f"\nTop {len(results)} results for query: '{query}'\n")
        for i, (doc, score) in enumerate(results, 1):
            click.echo(f"{i}. Score: {score:.3f}")
            click.echo(f"{'='*50}")
            click.echo(doc[:200] + "..." if len(doc) > 200 else doc)
            click.echo(f"{'='*50}\n")
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    search() 