import pytest
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


@pytest.mark.asyncio
async def test_update_user_profile(async_client, test_user, auth_headers):
    """Verify that an authenticated user can update their display name."""
    response = await async_client.patch(
        "/auth/me",
        headers=auth_headers,
        json={"username": "UpdatedDisplayName"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "UpdatedDisplayName"
    assert data["email"] == test_user.email
    assert data["auth_provider"] == "local"


@pytest.mark.asyncio
async def test_update_user_profile_blank_rejected(async_client, auth_headers):
    """Verify that updating display name to blank is rejected with 400 or 422."""
    response = await async_client.patch(
        "/auth/me",
        headers=auth_headers,
        json={"username": "   "},
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_export_conversations(async_client, db, test_user, auth_headers):
    """Verify that an authenticated user can export their conversation history."""
    conv = Conversation(
        user_id=test_user.id,
        title="Settings Test Chat",
        video_id="test_vid_123",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    msg_u = Message(conversation_id=conv.id, role="user", content="Hello test")
    msg_a = Message(conversation_id=conv.id, role="assistant", content="Hi test response")
    db.add_all([msg_u, msg_a])
    db.commit()

    response = await async_client.get("/conversations/export", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == test_user.email
    assert data["total_conversations"] >= 1
    found_conv = next((c for c in data["conversations"] if c["id"] == conv.id), None)
    assert found_conv is not None
    assert len(found_conv["messages"]) == 2
    assert found_conv["messages"][0]["content"] == "Hello test"


@pytest.mark.asyncio
async def test_clear_all_conversations(async_client, db, test_user, auth_headers):
    """Verify that an authenticated user can clear all their conversations."""
    conv1 = Conversation(user_id=test_user.id, title="Chat 1", video_id="vid1")
    conv2 = Conversation(user_id=test_user.id, title="Chat 2", video_id="vid2")
    db.add_all([conv1, conv2])
    db.commit()

    response = await async_client.delete("/conversations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "cleared_count" in data
    assert data["cleared_count"] >= 2

    # Verify conversations are gone
    remaining = db.query(Conversation).filter(Conversation.user_id == test_user.id).count()
    assert remaining == 0


@pytest.mark.asyncio
async def test_delete_user_account(async_client, db, auth_headers):
    """Verify that an authenticated user can delete their account cleanly."""
    # Create disposable user
    from app.services.auth_service import AuthService
    from app.auth.jwt import create_access_token
    auth_svc = AuthService()
    disp_email = "disposable.user@example.com"
    disp_token = auth_svc.login_or_create_google_user(
        db=db,
        google_id="disp_google_12345",
        email=disp_email,
        username="Disposable",
    )
    disp_headers = {"Authorization": f"Bearer {disp_token}"}

    # Delete account
    response = await async_client.delete("/auth/me", headers=disp_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Account deleted successfully."

    # Verify user record is deleted
    disp_user = db.query(User).filter(User.email == disp_email).first()
    assert disp_user is None
