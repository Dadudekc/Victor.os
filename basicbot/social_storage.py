import os
import json
import chromadb
import pandas as pd
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ✅ Choose embedding model: OpenAI or Local SentenceTransformer
USE_OPENAI = False  # Set to True if using OpenAI API

if USE_OPENAI:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    embedder = SentenceTransformer("all-MiniLM-L6-v2")  # Efficient local embedding model

# ✅ Initialize ChromaDB vector store
chroma_client = chromadb.PersistentClient(path="./vector_db")
collection = chroma_client.get_or_create_collection("social_posts")

def embed_text(text):
    """Returns a vector embedding for the given text."""
    if USE_OPENAI:
        response = openai_client.embeddings.create(input=[text], model="text-embedding-ada-002")
        return response["data"][0]["embedding"]
    else:
        return embedder.encode(text).tolist()

def store_post(platform, text, link=None):
    """
    Stores a social media post in ChromaDB with vectorized embeddings.

    :param platform: Social media platform (e.g., Twitter, LinkedIn)
    :param text: Post text content
    :param link: Post link (if available)
    """
    if not text.strip():
        return  # Ignore empty posts

    vector = embed_text(text)
    doc_id = f"{platform}_{hash(text)}"  # Unique ID for deduplication

    collection.add(
        ids=[doc_id],
        metadatas=[{"platform": platform, "link": link}],
        embeddings=[vector],
        documents=[text]
    )

    print(f"✅ Stored post from {platform}: {text[:50]}...")

def search_similar_posts(query, top_k=5):
    """
    Searches for similar posts in the vector database.

    :param query: Text query to find similar posts.
    :param top_k: Number of results to return.
    :return: List of similar posts.
    """
    query_vector = embed_text(query)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k
    )

    return [{"text": res["document"], "platform": res["metadata"]["platform"], "link": res["metadata"]["link"]}
            for res in results["documents"][0]]

# ✅ Example usage (Test search)
if __name__ == "__main__":
    query = "stock market trends"
    similar_posts = search_similar_posts(query)
    print("\n🔍 Similar Posts:")
    for post in similar_posts:
        print(f"- [{post['platform']}] {post['text'][:50]}...")
