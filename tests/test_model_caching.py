import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.services.embedding_service import (
    EmbeddingService,
    DEFAULT_EMBEDDING_MODEL_REVISION,
)
from app.services.reranker_service import (
    RerankerService,
    DEFAULT_RERANKER_MODEL_REVISION,
)


def test_embedding_service_uses_pinned_revision_and_local_cache():
    """Verify EmbeddingService passes pinned revision and attempts local_files_only=True."""
    with patch("app.services.embedding_service.SentenceTransformer") as mock_st_cls:
        mock_instance = MagicMock()
        mock_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_cls.return_value = mock_instance

        service = EmbeddingService()
        assert service.dimension == 384
        mock_st_cls.assert_called_once_with(
            "all-MiniLM-L6-v2",
            revision=DEFAULT_EMBEDDING_MODEL_REVISION,
            local_files_only=True,
        )


def test_embedding_service_custom_revision_override():
    """Verify custom revision override is honored by EmbeddingService."""
    with patch("app.services.embedding_service.SentenceTransformer") as mock_st_cls:
        mock_instance = MagicMock()
        mock_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_cls.return_value = mock_instance

        custom_rev = "custom_git_commit_sha_12345"
        service = EmbeddingService(model_name="all-MiniLM-L6-v2", revision=custom_rev)
        assert service.dimension == 384
        mock_st_cls.assert_called_once_with(
            "all-MiniLM-L6-v2",
            revision=custom_rev,
            local_files_only=True,
        )


def test_embedding_service_offline_failure_when_weights_missing(monkeypatch):
    """Verify EmbeddingService raises clear RuntimeError when HF_HUB_OFFLINE=1 and cache is missing."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")

    with patch("app.services.embedding_service.SentenceTransformer", side_effect=OSError("Local files missing")):
        with pytest.raises(RuntimeError) as exc_info:
            EmbeddingService()
        assert "HF_HUB_OFFLINE is set, but required embedding model" in str(exc_info.value)
        assert DEFAULT_EMBEDDING_MODEL_REVISION in str(exc_info.value)


def test_embedding_service_fallback_to_online_when_offline_not_forced():
    """Verify EmbeddingService falls back to downloading when local cache misses and offline is not forced."""
    with patch("app.services.embedding_service.SentenceTransformer") as mock_st_cls:
        mock_instance = MagicMock()
        mock_instance.get_sentence_embedding_dimension.return_value = 384
        # First call (local_files_only=True) fails, second call (online) succeeds
        mock_st_cls.side_effect = [OSError("Cache miss"), mock_instance]

        service = EmbeddingService()
        assert service.dimension == 384
        assert mock_st_cls.call_count == 2
        # First call attempted local
        assert mock_st_cls.call_args_list[0].kwargs.get("local_files_only") is True
        # Second call attempted online download
        assert "local_files_only" not in mock_st_cls.call_args_list[1].kwargs


def test_reranker_service_uses_pinned_revision_and_local_cache():
    """Verify RerankerService passes pinned revision and attempts local_files_only=True."""
    with patch("app.services.reranker_service.CrossEncoder") as mock_ce_cls:
        mock_instance = MagicMock()
        mock_ce_cls.return_value = mock_instance

        service = RerankerService()
        mock_ce_cls.assert_called_once_with(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            revision=DEFAULT_RERANKER_MODEL_REVISION,
            local_files_only=True,
        )


def test_reranker_service_offline_failure_when_weights_missing(monkeypatch):
    """Verify RerankerService raises clear RuntimeError when HF_HUB_OFFLINE=1 and cache is missing."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")

    with patch("app.services.reranker_service.CrossEncoder", side_effect=OSError("Local files missing")):
        with pytest.raises(RuntimeError) as exc_info:
            RerankerService()
        assert "HF_HUB_OFFLINE is set, but required reranker model" in str(exc_info.value)
        assert DEFAULT_RERANKER_MODEL_REVISION in str(exc_info.value)


def test_dockerfile_model_caching_and_offline_configuration():
    """Verify backend/Dockerfile configures HF_HOME and pre-downloads pinned models."""
    dockerfile = Path(__file__).resolve().parents[1] / "backend" / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text(encoding="utf-8")
    assert "HF_HOME=/home/ytgenius/.cache/huggingface" in content
    assert DEFAULT_EMBEDDING_MODEL_REVISION in content
    assert DEFAULT_RERANKER_MODEL_REVISION in content


def test_compose_hf_home_environment():
    """Verify docker-compose.yml defines HF_HOME environment variable."""
    compose_file = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    assert compose_file.exists()
    content = compose_file.read_text(encoding="utf-8")
    assert "HF_HOME=/home/ytgenius/.cache/huggingface" in content
