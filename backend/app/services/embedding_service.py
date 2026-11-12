import logging
import os
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger("ytgenius.embedding")

# Pinned revision for sentence-transformers/all-MiniLM-L6-v2 on Hugging Face
DEFAULT_EMBEDDING_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


class EmbeddingService:

    def __init__(self, model_name: str | None = None, revision: str | None = None):
        selected_model = (
            model_name
            or getattr(settings, "EMBEDDING_MODEL", None)
            or "all-MiniLM-L6-v2"
        )
        selected_revision = revision
        if selected_revision is None and selected_model in (
            "all-MiniLM-L6-v2",
            "sentence-transformers/all-MiniLM-L6-v2",
        ):
            selected_revision = DEFAULT_EMBEDDING_MODEL_REVISION

        # Attempt fast offline loading from local cache first to avoid runtime network dependencies
        try:
            self.model = SentenceTransformer(
                selected_model,
                revision=selected_revision,
                local_files_only=True,
            )
            logger.info("Loaded embedding model '%s' (revision: %s) from local cache.", selected_model, selected_revision)
        except Exception:
            if os.getenv("HF_HUB_OFFLINE", "0").lower() in ("1", "true"):
                raise RuntimeError(
                    f"HF_HUB_OFFLINE is set, but required embedding model '{selected_model}' "
                    f"(revision: {selected_revision}) was not found in the local cache."
                )
            logger.info("Embedding model '%s' not found in local cache; downloading...", selected_model)
            self.model = SentenceTransformer(
                selected_model,
                revision=selected_revision,
            )

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