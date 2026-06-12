import json
import threading
from pathlib import Path

import faiss
import numpy as np

from app.core.config import FAISS_INDEX_PATH
from app.services.embeddings import get_embedding, get_embeddings_batch

_lock = threading.Lock()

DIMENSION = 3072  # Gemini Embedding 2 output dimension
METADATA_PATH = FAISS_INDEX_PATH.with_suffix(".meta.json")


class VectorStore:
    def __init__(self) -> None:
        self.index: faiss.IndexFlatIP | None = None
        self.metadata: list[dict] = []
        self._load()

    def _load(self) -> None:
        index_file = Path(str(FAISS_INDEX_PATH) + ".index")
        if index_file.exists() and METADATA_PATH.exists():
            self.index = faiss.read_index(str(index_file))
            with open(METADATA_PATH, "r") as f:
                self.metadata = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(DIMENSION)
            self.metadata = []

    def _save(self) -> None:
        index_file = Path(str(FAISS_INDEX_PATH) + ".index")
        index_file.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_file))
        with open(METADATA_PATH, "w") as f:
            json.dump(self.metadata, f)

    def add_chunks(self, chunks: list[str], source: str, topic: str = "General") -> int:
        """Embed and store text chunks with metadata. Returns number of chunks added."""
        if not chunks:
            return 0

        embeddings = get_embeddings_batch(chunks)
        vectors = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(vectors)

        with _lock:
            self.index.add(vectors)
            for chunk in chunks:
                self.metadata.append({
                    "text": chunk,
                    "source": source,
                    "topic": topic,
                })
            self._save()

        return len(chunks)

    def search(self, query: str, top_k: int = 5, topic: str | None = None) -> list[dict]:
        """Search for the most relevant chunks given a query string."""
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vec = np.array([get_embedding(query)], dtype="float32")
        faiss.normalize_L2(query_vec)

        search_k = min(top_k * 3, self.index.ntotal) if topic else min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vec, search_k)

        results: list[dict] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            meta = self.metadata[idx]
            if topic and meta.get("topic", "").lower() != topic.lower():
                continue
            results.append({
                "text": meta["text"],
                "source": meta["source"],
                "topic": meta.get("topic", ""),
                "score": float(dist),
            })
            if len(results) >= top_k:
                break

        return results

    def get_topics(self) -> list[str]:
        """Return a deduplicated list of all topics in the store."""
        return sorted({m.get("topic", "General") for m in self.metadata})

    def get_sources(self) -> list[str]:
        """Return a deduplicated list of all sources in the store."""
        return sorted({m.get("source", "unknown") for m in self.metadata})

    def get_chunks(
        self,
        *,
        source: str | None = None,
        topic: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Return raw chunks (text + metadata) filtered by source and/or topic.

        Used by the seed-review flow which wants exhaustive coverage of a
        source rather than top-k semantic search.
        """
        results: list[dict] = []
        for meta in self.metadata:
            if source and meta.get("source", "").lower() != source.lower():
                continue
            if topic and meta.get("topic", "").lower() != topic.lower():
                continue
            results.append({
                "text": meta["text"],
                "source": meta.get("source", ""),
                "topic": meta.get("topic", ""),
            })
            if limit is not None and len(results) >= limit:
                break
        return results

    @property
    def total_chunks(self) -> int:
        return self.index.ntotal if self.index else 0


vector_store = VectorStore()
