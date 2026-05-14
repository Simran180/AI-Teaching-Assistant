from google import genai

from app.core.config import EMBEDDING_MODEL, GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

# Gemini embed API accepts multiple strings per call; split very large requests for reliability.
_EMBED_BATCH_SIZE = 100


def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    text = text.replace("\n", " ").strip()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return list(response.embeddings[0].values)


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts (same order as input)."""
    cleaned = [t.replace("\n", " ").strip() for t in texts]
    if not cleaned:
        return []

    all_vectors: list[list[float]] = []
    for i in range(0, len(cleaned), _EMBED_BATCH_SIZE):
        batch = cleaned[i : i + _EMBED_BATCH_SIZE]
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
        )
        all_vectors.extend(list(emb.values) for emb in response.embeddings)
    return all_vectors
