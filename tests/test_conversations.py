import pytest
from app.services.video_storage_service import VideoStorageService
from app.models.message import Message


@pytest.mark.asyncio
async def test_create_and_list_conversations(async_client, auth_headers):
    # 1. Create conversation with video_id
    resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "Test Chat", "video_id": "video_abc"},
    )
    assert resp.status_code == 200
    conv = resp.json()
    assert conv["title"] == "Test Chat"
    assert conv["video_id"] == "video_abc"
    conv_id = conv["id"]

    # 2. Create another conversation with different video_id
    resp2 = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "Other Chat", "video_id": "video_xyz"},
    )
    assert resp2.status_code == 200

    # 3. List all conversations
    list_all = await async_client.get("/conversations", headers=auth_headers)
    assert list_all.status_code == 200
    assert len(list_all.json()) >= 2

    # 4. Filter by video_id
    filtered = await async_client.get("/conversations?video_id=video_abc", headers=auth_headers)
    assert filtered.status_code == 200
    items = filtered.json()
    assert len(items) == 1
    assert items[0]["id"] == conv_id
    assert items[0]["video_id"] == "video_abc"


@pytest.mark.asyncio
async def test_send_conversation_message_restful(async_client, db, test_user, auth_headers, mock_rag_service):
    # Setup processed video
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="vid_qa_1",
        user_id=test_user.id,
        status="processed",
    )

    # Create conversation bound to vid_qa_1
    c_resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "YtGenius Q&A", "video_id": "vid_qa_1"},
    )
    conv_id = c_resp.json()["id"]

    # Send message via RESTful endpoint
    msg_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "What is the summary of this video?"},
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["conversation_id"] == conv_id
    assert data["role"] == "assistant"
    assert "vid_qa_1" in data["content"]
    assert len(data["sources"]) > 0

    # Verify messages persisted in DB
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.id.asc())
        .all()
    )
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "What is the summary of this video?"
    assert messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_prevent_cross_video_leakage_in_messages(async_client, db, test_user, auth_headers):
    # Setup two videos
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="video_alpha",
        user_id=test_user.id,
        status="processed",
    )
    storage.create_or_update_video(
        video_id="video_beta",
        user_id=test_user.id,
        status="processed",
    )

    # Conversation created for video_alpha
    c_resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "Alpha Chat", "video_id": "video_alpha"},
    )
    conv_id = c_resp.json()["id"]

    # Attempt to ask question for video_beta in video_alpha's conversation
    leak_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "Question about beta", "video_id": "video_beta"},
    )
    assert leak_resp.status_code == 400
    detail = leak_resp.json()["detail"].lower()
    assert "bound to video 'video_alpha'" in detail


@pytest.mark.asyncio
async def test_ask_backward_compatibility_and_video_binding(async_client, db, test_user, auth_headers, mock_rag_service):
    # Setup processed video
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="legacy_vid_001",
        user_id=test_user.id,
        status="processed",
    )

    # 1. Frontend calls /ask without conversation_id
    resp = await async_client.post(
        "/ask",
        headers=auth_headers,
        json={
            "video_id": "legacy_vid_001",
            "question": "Explain the introduction.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "conversation_id" in data
    conv_id = data["conversation_id"]

    # 2. Subsequent call with same conversation_id and video_id succeeds
    resp2 = await async_client.post(
        "/ask",
        headers=auth_headers,
        json={
            "video_id": "legacy_vid_001",
            "question": "Can you give more detail?",
            "conversation_id": conv_id,
        },
    )
    assert resp2.status_code == 200

    # 3. Call with same conversation_id but WRONG video_id is rejected (Defect 4 prevention)
    storage.create_or_update_video(
        video_id="different_vid_002",
        user_id=test_user.id,
        status="processed",
    )
    leak_resp = await async_client.post(
        "/ask",
        headers=auth_headers,
        json={
            "video_id": "different_vid_002",
            "question": "Sneak cross-video query",
            "conversation_id": conv_id,
        },
    )
    assert leak_resp.status_code == 400
    assert "bound to video" in leak_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_and_delete_conversation(async_client, auth_headers):
    # Create conversation
    create_resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "Initial Title"},
    )
    conv_id = create_resp.json()["id"]

    # Rename title
    patch_resp = await async_client.patch(
        f"/conversations/{conv_id}",
        headers=auth_headers,
        json={"title": "Updated Title"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Title"

    # Delete conversation
    del_resp = await async_client.delete(
        f"/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200

    # Verify deleted
    get_resp = await async_client.get(
        f"/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_conversation_user_isolation(async_client, auth_headers, test_user_2):
    """Verify that a user cannot access or read another user's conversation."""
    from app.auth.jwt import create_access_token

    # 1. User A creates a conversation
    resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "User A Private Conversation", "video_id": "video_user_a"},
    )
    assert resp.status_code == 200
    conv_id = resp.json()["id"]

    # 2. User B (different real user) attempts to access User A's conversation
    user_b_token = create_access_token(user_id=test_user_2.id)
    user_b_headers = {"Authorization": f"Bearer {user_b_token}"}

    get_resp = await async_client.get(
        f"/conversations/{conv_id}",
        headers=user_b_headers,
    )
    assert get_resp.status_code == 404

    # 3. User B attempts to post a message into User A's conversation
    msg_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=user_b_headers,
        json={"content": "Attempted cross-user injection"},
    )
    assert msg_resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_conversations_per_video_preserved(async_client, db, test_user, auth_headers, mock_rag_service):
    """Verify multiple distinct conversations can exist for the same video without mixing messages."""
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="shared_course_vid",
        user_id=test_user.id,
        status="processed",
    )

    # 1. Create first conversation for video
    resp1 = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "SQL Basics Thread", "video_id": "shared_course_vid"},
    )
    assert resp1.status_code == 200
    conv1_id = resp1.json()["id"]

    # 2. Create second conversation for same video
    resp2 = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "SQL Advanced Joins Thread", "video_id": "shared_course_vid"},
    )
    assert resp2.status_code == 200
    conv2_id = resp2.json()["id"]
    assert conv1_id != conv2_id

    # 3. Send message in conv1
    m1 = await async_client.post(
        f"/conversations/{conv1_id}/messages",
        headers=auth_headers,
        json={"content": "What is SELECT?"},
    )
    assert m1.status_code == 200

    # 4. Send message in conv2
    m2 = await async_client.post(
        f"/conversations/{conv2_id}/messages",
        headers=auth_headers,
        json={"content": "What is INNER JOIN?"},
    )
    assert m2.status_code == 200

    # 5. Verify conv1 messages contain only SELECT question
    c1_data = await async_client.get(f"/conversations/{conv1_id}", headers=auth_headers)
    assert c1_data.status_code == 200
    c1_msgs = c1_data.json()["messages"]
    assert len(c1_msgs) == 2
    assert c1_msgs[0]["content"] == "What is SELECT?"

    # 6. Verify conv2 messages contain only INNER JOIN question
    c2_data = await async_client.get(f"/conversations/{conv2_id}", headers=auth_headers)
    assert c2_data.status_code == 200
    c2_msgs = c2_data.json()["messages"]
    assert len(c2_msgs) == 2
    assert c2_msgs[0]["content"] == "What is INNER JOIN?"
