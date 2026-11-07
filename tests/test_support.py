import pytest
from app.models.bug_report import BugReport


@pytest.mark.asyncio
async def test_submit_bug_report_authenticated(async_client, test_user, auth_headers):
    """Verify that an authenticated user can submit a valid bug report."""
    payload = {
        "title": "Video playback sync delay",
        "description": "Timestamp citations jump 2 seconds ahead of audio on long videos.",
        "category": "video_playback",
    }
    response = await async_client.post(
        "/api/support/bug-reports",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["user_id"] == test_user.id
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["category"] == "video_playback"
    assert data["status"] == "open"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_submit_bug_report_unauthenticated(async_client):
    """Verify that unauthenticated users cannot submit bug reports (401)."""
    payload = {
        "title": "Unauthorized attempt",
        "description": "This should be rejected because no auth token is provided.",
    }
    response = await async_client.post(
        "/api/support/bug-reports",
        json=payload,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_bug_report_validation_errors(async_client, auth_headers):
    """Verify validation on short/empty titles and descriptions (422)."""
    # 1. Title too short (<3 chars)
    resp_short_title = await async_client.post(
        "/api/support/bug-reports",
        json={"title": "No", "description": "Valid description that meets minimum length."},
        headers=auth_headers,
    )
    assert resp_short_title.status_code == 422

    # 2. Description too short (<10 chars)
    resp_short_desc = await async_client.post(
        "/api/support/bug-reports",
        json={"title": "Valid title", "description": "Too short"},
        headers=auth_headers,
    )
    assert resp_short_desc.status_code == 422

    # 3. Title too long (>200 chars)
    resp_long_title = await async_client.post(
        "/api/support/bug-reports",
        json={"title": "A" * 201, "description": "Valid description that meets minimum length."},
        headers=auth_headers,
    )
    assert resp_long_title.status_code == 422


@pytest.mark.asyncio
async def test_submit_bug_report_default_category(async_client, test_user, auth_headers):
    """Verify that category defaults to 'general' when omitted or unknown."""
    payload = {
        "title": "General UI question",
        "description": "Dark mode contrast on secondary buttons looks a bit soft.",
    }
    response = await async_client.post(
        "/api/support/bug-reports",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["category"] == "general"
