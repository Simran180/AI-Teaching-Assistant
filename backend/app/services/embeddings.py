from google import genai

from app.core.config import EMBEDDING_MODEL, GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)


def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    text = text.replace("\n", " ").strip()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )
    return [embedding.values for embedding in response.embeddings]


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    cleaned = [t.replace("\n", " ").strip() for t in texts]
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[
        {"parts": [{"text": text}]} for text in cleaned
    ]
    )
    print("Embeddings created: ",len(response.embeddings))
    return [embedding.values for embedding in response.embeddings]
