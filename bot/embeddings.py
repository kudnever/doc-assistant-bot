import hashlib
import itertools
import math

from .config import settings


def embed(texts: list[str]) -> list[list[float]]:
    if settings.voyage_api_key:
        return _voyage_embed(texts)
    return [_stub_embed(text) for text in texts]


def _voyage_embed(texts: list[str]) -> list[list[float]]:
    import voyageai

    client = voyageai.Client(api_key=settings.voyage_api_key)
    vectors: list[list[float]] = []
    for i in range(0, len(texts), 128):
        batch = texts[i : i + 128]
        response = client.embed(batch, model="voyage-3-lite", output_dimension=512)
        vectors.extend([list(vector) for vector in response.embeddings])
    return vectors


def _stub_embed(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    values = []
    for byte in itertools.islice(itertools.cycle(digest), 512):
        values.append((byte / 127.5) - 1.0)

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
