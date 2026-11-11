import numpy as np
import pytest
from unittest.mock import MagicMock
from app.services.qdrant_service import QdrantVectorStore


def test_production_rejects_in_memory_qdrant(monkeypatch):
    """Verify that in production, falling back to in-memory Qdrant raises ValueError."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("QDRANT_URL", raising=False)

    with pytest.raises(ValueError, match="forbidden in production environments"):
        QdrantVectorStore(url=":memory:")


def test_development_allows_in_memory_qdrant(monkeypatch):
    """Verify that development/test environments permit in-memory Qdrant."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    store = QdrantVectorStore(url=":memory:")
    assert store.client is not None
    assert store.is_healthy() is True


def test_deterministic_point_ids_and_idempotent_reprocessing():
    """
    Verify that re-ingesting a video with fewer chunks clears previous vectors
    and replaces them idempotently without orphaned points.
    """
    store = QdrantVectorStore(url=":memory:")
    store.create_collection()

    vid = "test_reprocess_vid"

    # 1. Initial ingestion with 4 chunks
    embeddings_1 = [np.array([0.1] * 384) for _ in range(4)]
    chunks_1 = [
        {"video_id": vid, "text": f"Chunk {i}", "start_time": i * 10.0, "end_time": (i + 1) * 10.0}
        for i in range(4)
    ]
    store.add_documents(embeddings_1, chunks_1)
    assert store.count_video_chunks(vid) == 4

    # 2. Re-ingestion with reduced chunks (2 chunks)
    embeddings_2 = [np.array([0.2] * 384) for _ in range(2)]
    chunks_2 = [
        {"video_id": vid, "text": f"New Chunk {i}", "start_time": i * 20.0, "end_time": (i + 1) * 20.0}
        for i in range(2)
    ]
    store.add_documents(embeddings_2, chunks_2, delete_existing=True)

    # 3. Verify exactly 2 chunks remain (zero orphaned vectors from run 1)
    assert store.count_video_chunks(vid) == 2


def test_deletion_and_cleanup_idempotent():
    """Verify that deleting a video multiple times is safe and idempotent."""
    store = QdrantVectorStore(url=":memory:")
    store.create_collection()

    vid = "idempotent_del_vid"
    embeddings = [np.array([0.1] * 384)]
    chunks = [{"video_id": vid, "text": "Sample text", "start_time": 0.0, "end_time": 5.0}]
    store.add_documents(embeddings, chunks)
    assert store.count_video_chunks(vid) == 1

    # First delete
    store.delete_video(vid)
    assert store.count_video_chunks(vid) == 0

    # Second delete (must succeed idempotently without error)
    store.delete_video(vid)
    assert store.count_video_chunks(vid) == 0


def test_qdrant_dimension_matching_preserves_collection():
    """Verify that calling create_collection with matching dimension preserves existing data."""
    store = QdrantVectorStore(url=":memory:")
    store.create_collection(vector_size=384)

    vid = "match_dim_vid"
    embeddings = [np.array([0.1] * 384)]
    chunks = [{"video_id": vid, "text": "Preserved text", "start_time": 0.0, "end_time": 5.0}]
    store.add_documents(embeddings, chunks)
    assert store.count_video_chunks(vid) == 1

    # Calling create_collection again with matching dimension
    store.create_collection(vector_size=384)
    # Existing data must remain completely intact
    assert store.count_video_chunks(vid) == 1


def test_qdrant_dimension_mismatch_rejects_and_preserves_collection():
    """Verify that attempting to initialize collection with mismatching dimensions fails clearly and preserves data."""
    store = QdrantVectorStore(url=":memory:")
    store.create_collection(vector_size=384)

    vid = "preserve_on_err_vid"
    embeddings = [np.array([0.1] * 384)]
    chunks = [{"video_id": vid, "text": "Preserved data", "start_time": 0.0, "end_time": 5.0}]
    store.add_documents(embeddings, chunks)
    assert store.count_video_chunks(vid) == 1

    # Attempting to call create_collection with conflicting vector dimension must raise ValueError
    with pytest.raises(ValueError, match="Qdrant collection dimension mismatch"):
        store.create_collection(vector_size=512)

    # Verify that existing collection and data were preserved without destructive recreation
    assert store.count_video_chunks(vid) == 1


def test_qdrant_add_documents_dimension_mismatch_raises_error(monkeypatch):
    """Verify that adding documents with incorrect embedding dimension raises ValueError."""
    store = QdrantVectorStore(url=":memory:")
    store.create_collection(vector_size=384)

    vid = "mismatch_dim_vid"
    wrong_embeddings = [np.array([0.1] * 512)]
    chunks = [{"video_id": vid, "text": "Mismatch text", "start_time": 0.0, "end_time": 5.0}]

    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        store.add_documents(wrong_embeddings, chunks)


def test_rag_service_dimension_mismatch_raises_error(monkeypatch):
    """Verify RAGService fails fast when model dimension does not match VECTOR_DIMENSION."""
    from app.services.rag_service import RAGService
    monkeypatch.setattr("app.services.rag_service.settings.VECTOR_DIMENSION", 512)

    with pytest.raises(ValueError, match="Embedding model dimension mismatch"):
        RAGService()
