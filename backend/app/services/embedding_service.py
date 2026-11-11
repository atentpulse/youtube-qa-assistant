from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:

    def __init__(self, model_name: str | None = None):
        selected_model = (
            model_name
            or getattr(settings, "EMBEDDING_MODEL", None)
            or "all-MiniLM-L6-v2"
        )
        self.model = SentenceTransformer(selected_model)

    @property
    def dimension(self) -> int:
        """Returns the actual output dimension of the underlying embedding model."""
        if hasattr(self.model, "get_sentence_embedding_dimension"):
            method = getattr(self.model, "get_sentence_embedding_dimension")
            if callable(method):
                try:
                    dim = method()
                    if isinstance(dim, int) and type(dim) is int:
                        return dim
                except Exception:
                    pass
        return getattr(settings, "VECTOR_DIMENSION", 384)


    def embed_documents(
        self,
        texts: list[str],
        batch_size: int = 32,
    ):

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

        return embeddings


    def embed_query(
        self,
        query: str,
    ):

        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embedding