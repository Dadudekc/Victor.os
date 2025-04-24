"""
Swap-in backend: if chromadb installed -> use it, else fall back to JSON list.
"""
import json, pathlib, logging
import numpy as np

# Use a path relative to the project root, assuming this file is also at the root
DB_PATH = pathlib.Path("memory/vector_db.json")

def upsert(id_: str, text: str):
    """Adds or updates an entry in the JSON file."""
    logging.debug(f"VectorDB (JSON Stub) Upsert: id='{id_}', text='{text[:50]}...'")
    data = _load()
    data[id_] = text
    _save(data)

def query(text: str, top_k=5):
    """Performs a naive search, returning the first top_k values."""
    logging.debug(f"VectorDB (JSON Stub) Query: text='{text[:50]}...', top_k={top_k}")
    data = _load()
    docs = list(data.values())
    # build vocabulary from query tokens
    tokens = text.lower().split()
    vocab = list(set(tokens))
    def _vectorize(doc: str):
        words = doc.lower().split()
        return np.array([words.count(tok) for tok in vocab], dtype=float)
    q_vec = _vectorize(text)
    sims = []
    for doc in docs:
        d_vec = _vectorize(doc)
        denom = np.linalg.norm(q_vec) * np.linalg.norm(d_vec)
        sim = float(np.dot(q_vec, d_vec) / denom) if denom else 0.0
        sims.append(sim)
    # rank by similarity and return top_k documents
    top_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
    result = [docs[i] for i in top_idx]
    logging.debug(f"VectorDB (JSON Stub) Result Count: {len(result)}")
    return result

def _load() -> dict:
    """Loads the JSON data file."""
    try:
        if DB_PATH.exists():
            return json.loads(DB_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {DB_PATH}: {e}. Returning empty dict.")
    except Exception as e:
         logging.error(f"Error loading {DB_PATH}: {e}. Returning empty dict.")
    return {}

def _save(d: dict):
    """Saves the dictionary to the JSON file."""
    try:
        DB_PATH.parent.mkdir(exist_ok=True, parents=True)
        DB_PATH.write_text(json.dumps(d, indent=2), encoding='utf-8')
    except Exception as e:
        logging.error(f"Error saving to {DB_PATH}: {e}") 