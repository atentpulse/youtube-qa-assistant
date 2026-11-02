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


class QdrantVectorStore:

    COLLECTION_NAME = "youtube_video_chunks"

    def __init__(self, url: str | None = None, api_key: str | None = None):

        qdrant_url = url or os.getenv("QDRANT_URL")
        qdrant_api_key = api_key or os.getenv("QDRANT_API_KEY")

        if not qdrant_url or qdrant_url == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
            )


    def create_collection(
        self,
        vector_size: int = 384,
    ):

        try:
            collections = self.client.get_collections()
            collection_names = [
                collection.name
                for collection in collections.collections
            ]

            if self.COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                print("Collection created successfully!")
        except Exception as error:
            print(f"Warning: Could not initialize Qdrant collection on startup: {error}")

        else:

            print(
                "Collection already exists!"
            )


        # Create index for video_id filtering
        self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="video_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )

        print(
            "video_id payload index ready!"
        )


    def add_documents(
        self,
        embeddings,
        chunks,
    ):

        points = []

        for embedding, chunk in zip(
            embeddings,
            chunks,
        ):

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={
                    "video_id": chunk["video_id"],
                    "text": chunk["text"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                },
            )

            points.append(point)


        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )

        print(
            f"{len(points)} chunks added to Qdrant!"
        )


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
                    "start_time": point.payload[
                        "start_time"
                    ],
                    "end_time": point.payload[
                        "end_time"
                    ],
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

        print(
            f"Deleted Qdrant vectors for video: "
            f"{video_id}"
        )