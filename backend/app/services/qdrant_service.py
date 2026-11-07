import logging
import os
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

load_dotenv()
logger = logging.getLogger("ytgenius.qdrant")


class QdrantVectorStore:
    COLLECTION_NAME = "youtube_video_chunks"

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ):
        qdrant_url = url or os.getenv("QDRANT_URL")
        qdrant_api_key = api_key or os.getenv("QDRANT_API_KEY")
        environment = os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development"
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
        vector_size: int = 384,
    ):
        try:
            collections = self.client.get_collections()
            collection_names = [
                collection.name for collection in collections.collections
            ]

            if self.COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Collection '%s' created successfully.", self.COLLECTION_NAME)
            else:
                logger.debug("Collection '%s' already exists.", self.COLLECTION_NAME)

            # Create index for video_id filtering safely
            try:
                self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name="video_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception as idx_err:
                logger.debug("Notice on payload index creation: %s", idx_err)

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
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=batch,
            )

        logger.info("%d chunks added to Qdrant for video %s", len(points), video_id)

    def search(
        self,
        query_embedding,
        video_id: str,
        top_k: int = 3,
    ):
        results = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
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
            collection_name=self.COLLECTION_NAME,
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
            collection_name=self.COLLECTION_NAME,
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
            collection_name=self.COLLECTION_NAME,
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
