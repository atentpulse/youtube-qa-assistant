import pytest
from app.services.video_storage_service import VideoStorageService


@pytest.mark.asyncio
async def test_complete_e2e_workflow(async_client, db, mock_rag_service):
    # -------------------------------------------------------------
    # 1. Register User
    # -------------------------------------------------------------
    reg_resp = await async_client.post(
        "/auth/register",
        json={
            "username": "e2e_user",
            "email": "e2e_user@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert reg_resp.status_code == 200
    user_id = reg_resp.json()["id"]

    # Mark user as email verified in DB
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    user.email_verified = True
    db.commit()

    # -------------------------------------------------------------
    # 2. Login User
    # -------------------------------------------------------------
    login_resp = await async_client.post(
        "/auth/login",
        json={
            "email": "e2e_user@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------
    # 3. Check Current User & Users Me Alias
    # -------------------------------------------------------------
    me_resp = await async_client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "e2e_user@example.com"

    users_me_resp = await async_client.get("/users/me", headers=headers)
    assert users_me_resp.status_code == 200
    assert users_me_resp.json()["id"] == user_id

    # -------------------------------------------------------------
    # 4. Process Video
    # -------------------------------------------------------------
    # Setup video in storage as processed
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="e2e_vid_001",
        user_id=user_id,
        status="processed",
        segments=12,
        chunks=4,
        title="E2E Demonstration Video",
    )

    # Check status
    status_resp = await async_client.get(
        "/videos/e2e_vid_001/status",
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "processed"

    # List videos
    list_resp = await async_client.get("/videos", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # -------------------------------------------------------------
    # 5. Create Conversation Bound to Video
    # -------------------------------------------------------------
    conv_resp = await async_client.post(
        "/conversations",
        headers=headers,
        json={"title": "E2E Discussion", "video_id": "e2e_vid_001"},
    )
    assert conv_resp.status_code == 200
    conv_id = conv_resp.json()["id"]
    assert conv_resp.json()["video_id"] == "e2e_vid_001"

    # -------------------------------------------------------------
    # 6. RESTful Message Exchange
    # -------------------------------------------------------------
    msg_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "What is the key takeaway?"},
    )
    assert msg_resp.status_code == 200
    assert msg_resp.json()["role"] == "assistant"
    assert "e2e_vid_001" in msg_resp.json()["content"]

    # Retrieve conversation messages
    msgs_resp = await async_client.get(
        f"/conversations/{conv_id}/messages",
        headers=headers,
    )
    assert msgs_resp.status_code == 200
    assert len(msgs_resp.json()["messages"]) == 2

    # -------------------------------------------------------------
    # 7. Backward Compatibility /ask Endpoint
    # -------------------------------------------------------------
    ask_resp = await async_client.post(
        "/ask",
        headers=headers,
        json={
            "video_id": "e2e_vid_001",
            "question": "Can you summarize step 2?",
            "conversation_id": conv_id,
        },
    )
    assert ask_resp.status_code == 200
    assert "answer" in ask_resp.json()
    assert ask_resp.json()["conversation_id"] == conv_id

    # -------------------------------------------------------------
    # 8. Token Refresh
    # -------------------------------------------------------------
    refresh_resp = await async_client.post("/auth/refresh", headers=headers)
    assert refresh_resp.status_code == 200
    new_token = refresh_resp.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # -------------------------------------------------------------
    # 9. Cleanup Conversation
    # -------------------------------------------------------------
    del_resp = await async_client.delete(
        f"/conversations/{conv_id}",
        headers=new_headers,
    )
    assert del_resp.status_code == 200
