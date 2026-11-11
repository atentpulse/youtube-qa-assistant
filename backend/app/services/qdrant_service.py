import logging
import os
import time
import uuid

from dotenv import load_dotenv

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)

from app.core import settings

load_dotenv()
logger = logging.getLogger("ytgenius.qdrant")


class QdrantVectorStore:
    COLLECTION_NAME = getattr(settings, "QDRANT_COLLECTION", "youtube_video_chunks")

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
        collection_name: str | None = None,
    ):
        self.collection_name = (
            collection_name
            or getattr(settings, "QDRANT_COLLECTION", None)
            or self.COLLECTION_NAME
        )
        qdrant_url = url if url is not None else (settings.QDRANT_URL or os.getenv("QDRANT_URL"))
        qdrant_api_key = api_key if api_key is not None else (settings.QDRANT_API_KEY or os.getenv("QDRANT_API_KEY"))
        environment = os.getenv("ENVIRONMENT") or os.getenv("ENV") or settings.ENVIRONMENT or "development"
        is_testing = os.getenv("TESTING") == "1"

        # Production must not fall back to in-memory Qdrant
        if environment.lower() == "production" and not is_testing:
            if not qdrant_url or qdrant_url == ":memory:":
                raise ValueError(
                    "Production configuration error: QDRANT_URL must be set to a valid remote cluster. "
                    "In-memory Qdrant (:memory:) is forbidden in production environments."
                )

        if not qdrant_url or qdrant_url == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                timeout=timeout,
            )

    def is_healthy(self) -> bool:
        """Lightweight readiness probe for Qdrant service."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.warning("Qdrant health check failed: %s", e)
            return False

    def create_collection(
        self,
        vector_size: int | None = None,
    ):
        try:
            target_size = vector_size or getattr(settings, "VECTOR_DIMENSION", 384)
            collections = self.client.get_collections()
            collection_names = [
                collection.name for collection in collections.collections
            ]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=target_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Collection '%s' created successfully.", self.collection_name)
            else:
                # Verify existing collection dimensions match target_size
                info = self.client.get_collection(self.collection_name)
                vectors_cfg = getattr(getattr(info, "config", None), "params", None)
                if vectors_cfg:
                    v_params = getattr(vectors_cfg, "vectors", None)
                    existing_dim = None
                    if hasattr(v_params, "size"):
                        existing_dim = v_params.size
                    elif isinstance(v_params, dict) and "" in v_params:
                        existing_dim = getattr(v_params[""], "size", None)

                    if existing_dim is not None and existing_dim != target_size:
                        raise ValueError(
                            f"Qdrant collection dimension mismatch: Existing collection '{self.collection_name}' has dimension "
                            f"{existing_dim}, but requested dimension is {target_size}. Cannot index incompatible vectors."
                        )

                logger.debug("Collection '%s' already exists with matching dimension.", self.collection_name)

            # Create index for video_id filtering safely
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="video_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception as idx_err:
                logger.debug("Notice on payload index creation: %s", idx_err)

        except ValueError:
            raise
        except Exception as error:
            logger.warning("Could not initialize Qdrant collection on startup: %s", error)

    def add_documents(
        self,
        embeddings,
        chunks,
        batch_size: int = 64,
        delete_existing: bool = True,
    ):
        if not chunks:
            return

        if embeddings is not None and len(embeddings) > 0:
            actual_dim = len(embeddings[0])
            expected_dim = getattr(settings, "VECTOR_DIMENSION", 384)
            if actual_dim != expected_dim:
                raise ValueError(
                    f"Embedding dimension mismatch: Attempted to add vectors of dimension {actual_dim} "
                    f"to collection configured for dimension {expected_dim}."
                )

        video_id = chunks[0].get("video_id")
        if delete_existing and video_id:
            try:
                self.delete_video(video_id)
            except Exception as e:
                logger.warning(
                    "Failed to clear previous vectors for %s before ingestion: %s",
                    video_id,
                    e,
                )

        points = []
        for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
            # Deterministic UUIDv5 ensures idempotency across reprocessing and retries
            deterministic_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk['video_id']}_chunk_{i}")
            )
            point = PointStruct(
                id=deterministic_id,
                vector=embedding.tolist(),
                payload={
                    "video_id": chunk["video_id"],
                    "text": chunk["text"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                },
            )
            points.append(point)

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=batch,
                    )
                    break
                except Exception as exc:
                    if attempt == max_retries - 1:
                        logger.error(
                            "Qdrant batch upsert failed after %d attempts for video %s: %s",
                            max_retries,
                            video_id,
                            exc,
                        )
                        raise
                    logger.warning(
                        "Qdrant batch upsert attempt %d/%d failed for video %s: %s; retrying...",
                        attempt + 1,
                        max_retries,
                        video_id,
                        exc,
                    )
                    time.sleep(0.5 * (attempt + 1))

        logger.info("%d chunks added to Qdrant for video %s", len(points), video_id)

    def search(
        self,
        query_embedding,
        video_id: str,
        top_k: int = 3,
    ):
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="video_id",
                        match=MatchValue(
                            value=video_id,
                        ),
                    )
                ]
            ),
            limit=top_k,
        )

        search_results = []
        for point in results.points:
            search_results.append(
                {
                    "text": point.payload["text"],
                    "start_time": point.payload["start_time"],
                    "end_time": point.payload["end_time"],
                    "score": point.score,
                }
            )

        return search_results

    def video_exists(
        self,
        video_id: str,
    ) -> bool:
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="video_id",
                        match=MatchValue(
                            value=video_id,
                        ),
                    )
                ]
            ),
            limit=1,
        )
        points = results[0]
        return len(points) > 0

    def count_video_chunks(
        self,
        video_id: str,
    ) -> int:
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="video_id",
                        match=MatchValue(
                            value=video_id,
                        ),
                    )
                ]
            ),
            exact=True,
        )
        return result.count

    def delete_video(
        self,
        video_id: str,
    ):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="video_id",
                            match=models.MatchValue(
                                value=video_id,
                            ),
                        )
                    ]
                )
            ),
        )
        logger.info("Deleted Qdrant vectors for video: %s", video_id)
