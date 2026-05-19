from fastembed import TextEmbedding

from .config import settings


_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=settings.embedding_model)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = list(model.embed(texts))
    return [vec.tolist() for vec in vectors]
