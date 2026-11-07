from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy.exc import OperationalError


@pytest.mark.asyncio
async def test_legacy_health_endpoint(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_liveness_probe_endpoint(async_client):
    res = await async_client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_probe_all_healthy(async_client):
    with patch("app.main.QdrantVectorStore") as mock_qdrant_cls:
        mock_instance = MagicMock()
        mock_instance.is_healthy.return_value = True
        mock_qdrant_cls.return_value = mock_instance

        res = await async_client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["qdrant"] == "ok"


@pytest.mark.asyncio
async def test_readiness_probe_database_failure(async_client):
    with patch("app.main.QdrantVectorStore") as mock_qdrant_cls:
        mock_instance = MagicMock()
        mock_instance.is_healthy.return_value = True
        mock_qdrant_cls.return_value = mock_instance

        # Mock DB execute failure
        with patch("sqlalchemy.orm.Session.execute", side_effect=OperationalError("connection refused", {}, Exception())):
            res = await async_client.get("/health/ready")
            assert res.status_code == 503
            data = res.json()
            assert data["status"] == "unhealthy"
            assert "unhealthy" in data["checks"]["database"]
            assert data["checks"]["qdrant"] == "ok"


@pytest.mark.asyncio
async def test_readiness_probe_qdrant_failure(async_client):
    with patch("app.main.QdrantVectorStore") as mock_qdrant_cls:
        mock_instance = MagicMock()
        mock_instance.is_healthy.return_value = False
        mock_qdrant_cls.return_value = mock_instance

        res = await async_client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "ok"
        assert "unhealthy" in data["checks"]["qdrant"]
