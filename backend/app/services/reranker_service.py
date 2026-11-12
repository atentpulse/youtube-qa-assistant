import logging
import os
from sentence_transformers import CrossEncoder

from app.core.config import settings

logger = logging.getLogger("ytgenius.reranker")

# Pinned revision for cross-encoder/ms-marco-MiniLM-L-6-v2 on Hugging Face
DEFAULT_RERANKER_MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


class RerankerService:

    def __init__(self, model_name: str | None = None, revision: str | None = None):

        logger.info("Loading reranker model...")

        selected_model = (
            model_name
            or getattr(settings, "RERANKER_MODEL", None)
            or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        selected_revision = revision
        if selected_revision is None and selected_model == "cross-encoder/ms-marco-MiniLM-L-6-v2":
            selected_revision = DEFAULT_RERANKER_MODEL_REVISION

        # Attempt fast offline loading from local cache first to avoid runtime network dependencies
        try:
            self.model = CrossEncoder(
                selected_model,
                revision=selected_revision,
                local_files_only=True,
            )
            logger.info("Loaded reranker model '%s' (revision: %s) from local cache.", selected_model, selected_revision)
        except Exception:
            if os.getenv("HF_HUB_OFFLINE", "0").lower() in ("1", "true"):
                raise RuntimeError(
                    f"HF_HUB_OFFLINE is set, but required reranker model '{selected_model}' "
                    f"(revision: {selected_revision}) was not found in the local cache."
                )
            logger.info("Reranker model '%s' not found in local cache; downloading...", selected_model)
            self.model = CrossEncoder(
                selected_model,
                revision=selected_revision,
            )

        logger.info("Reranker model loaded successfully.")


    def rerank(
        self,
        question: str,
        results: list,
        top_k: int = 5,
    ) -> list:

        if not results:
            return []

        pairs = [
            (question, result["text"])
            for result in results
        ]

        scores = self.model.predict(pairs)

        reranked_results = []

        for result, score in zip(results, scores):
            reranked_result = result.copy()
            reranked_result["rerank_score"] = float(score)
            reranked_results.append(reranked_result)

        reranked_results.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return reranked_results[:top_k]
