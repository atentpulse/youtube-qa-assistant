import logging
from sentence_transformers import CrossEncoder

from app.core.config import settings

logger = logging.getLogger("ytgenius.reranker")


class RerankerService:

    def __init__(self, model_name: str | None = None):

        logger.info("Loading reranker model...")

        selected_model = (
            model_name
            or getattr(settings, "RERANKER_MODEL", None)
            or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self.model = CrossEncoder(selected_model)

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
