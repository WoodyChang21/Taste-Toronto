import chromadb
from pathlib import Path

_client = None
_collection = None

CHROMA_PATH = str(Path(__file__).parent.parent / "data" / "chroma_store")
COLLECTION_NAME = "toronto_restaurants"


def get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def reset_collection() -> None:
    global _client, _collection
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    _client = None
