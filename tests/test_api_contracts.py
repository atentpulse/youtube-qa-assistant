from datetime import timedelta
import pytest
from app.auth.jwt import create_access_token, create_refresh_token
from app.models.message import Message
from app.services.video_storage_service import VideoStorageService


@pytest.mark.asyncio
async def test_auth_headers_missing_and_malformed(async_client):
    """Verify that protected endpoints reject missing and malformed authorization headers with 401."""
    # 1. Missing Authorization header
    resp_missing = await async_client.get("/auth/me")
    assert resp_missing.status_code == 401
    assert "not authenticated" in resp_missing.json()["detail"].lower()

    # 2. Malformed scheme (Basic instead of Bearer)
    resp_basic = await async_client.get(
        "/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert resp_basic.status_code == 401
    assert "not authenticated" in resp_basic.json()["detail"].lower()

    # 3. Empty Bearer token
    resp_empty = await async_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer "},
    )
    assert resp_empty.status_code == 401

    # 4. Tampered / invalid token signature
    resp_tampered = await async_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalid.signature"},
    )
    assert resp_tampered.status_code == 401
    assert "invalid or expired authentication token" in resp_tampered.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_response_schema_fields(async_client, test_user, auth_headers):
    """Verify UserResponse schema contract includes email_verified and created_at."""
    # 1. Test via registration
    reg_resp = await async_client.post(
        "/auth/register",
        json={
            "username": "contractuser",
            "email": "contractuser@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["username"] == "contractuser"
    assert reg_data["email"] == "contractuser@example.com"
    assert reg_data["email_verified"] is False
    assert "created_at" in reg_data
    assert reg_data["created_at"] is not None

    # 2. Test via /auth/me
    me_resp = await async_client.get("/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == test_user.username
    assert me_data["email"] == test_user.email
    assert me_data["email_verified"] is True
    assert "created_at" in me_data
    assert me_data["created_at"] is not None


@pytest.mark.asyncio
async def test_auth_request_validation(async_client):
    """Verify registration request validation rejects malformed inputs with 422."""
    # 1. Short password (< 6 chars)
    short_pw = await async_client.post(
        "/auth/register",
        json={
            "username": "validname",
            "email": "valid@example.com",
            "password": "123",
        },
    )
    assert short_pw.status_code == 422

    # 2. Invalid email format
    bad_email = await async_client.post(
        "/auth/register",
        json={
            "username": "validname",
            "email": "not-an-email",
            "password": "ValidPassword123!",
        },
    )
    assert bad_email.status_code == 422

    # 3. Short username (< 3 chars)
    short_name = await async_client.post(
        "/auth/register",
        json={
            "username": "ab",
            "email": "valid2@example.com",
            "password": "ValidPassword123!",
        },
    )
    assert short_name.status_code == 422


@pytest.mark.asyncio
async def test_video_endpoints_validation_and_errors(
    async_client, auth_headers, auth_headers_2, db, test_user, mock_rag_service
):
    """Verify video endpoints validation, 400 on invalid URL, and 404 on missing/cross-user resources."""
    # Wire delete_video to check actual storage existence
    def mock_delete_video(db, user_id, video_id):
        storage = VideoStorageService(db)
        if not storage.get_video(video_id=video_id, user_id=user_id):
            raise ValueError("Video not found.")
        storage.delete_video(video_id=video_id, user_id=user_id)
        return {"status": "deleted", "video_id": video_id}

    mock_rag_service.delete_video.side_effect = mock_delete_video

    # 1. Invalid YouTube URL rejected with 400
    mock_rag_service.process_video.side_effect = ValueError("Invalid YouTube URL")
    bad_url_resp = await async_client.post(
        "/videos/process",
        headers=auth_headers,
        json={"url": "https://notyoutube.com/watch?v=invalid"},
    )
    assert bad_url_resp.status_code == 400
    assert "invalid youtube url" in bad_url_resp.json()["detail"].lower()

    # 2. Missing URL field rejected with 422
    empty_url_resp = await async_client.post(
        "/videos/process",
        headers=auth_headers,
        json={},
    )
    assert empty_url_resp.status_code == 422

    # 3. Non-existent video status returns 404
    status_404 = await async_client.get(
        "/videos/nonexistent_vid_999/status",
        headers=auth_headers,
    )
    assert status_404.status_code == 404
    assert status_404.json()["detail"] == "Video not found."

    # 4. Non-existent video deletion returns 404
    del_404 = await async_client.delete(
        "/videos/nonexistent_vid_999",
        headers=auth_headers,
    )
    assert del_404.status_code == 404
    assert del_404.json()["detail"] == "Video not found."

    # 5. User 2 cannot delete User 1's video (cross-user isolation returns 404)
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="user1_private_vid",
        user_id=test_user.id,
        status="processed",
        title="User 1 Private Video",
    )

    del_cross = await async_client.delete(
        "/videos/user1_private_vid",
        headers=auth_headers_2,
    )
    assert del_cross.status_code == 404


@pytest.mark.asyncio
async def test_conversation_messages_pagination_and_ownership(
    async_client, db, test_user, auth_headers, auth_headers_2
):
    """Verify GET /conversations/{id}/messages pagination and cross-user 404 isolation."""
    # 1. Create conversation for User 1
    c_resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "Pagination Chat", "video_id": "vid_pag_1"},
    )
    conv_id = c_resp.json()["id"]

    # 2. Add 5 messages directly to DB
    for i in range(1, 6):
        role = "user" if i % 2 != 0 else "assistant"
        db.add(Message(conversation_id=conv_id, role=role, content=f"Message {i}"))
    db.commit()

    # 3. Retrieve messages with limit=2
    pag_resp = await async_client.get(
        f"/conversations/{conv_id}/messages?limit=2",
        headers=auth_headers,
    )
    assert pag_resp.status_code == 200
    pag_data = pag_resp.json()
    assert "messages" in pag_data
    assert len(pag_data["messages"]) == 2
    assert "next_cursor" in pag_data
    assert pag_data["next_cursor"] is not None

    # 4. User 2 access to User 1's messages returns 404
    cross_msg_resp = await async_client.get(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers_2,
    )
    assert cross_msg_resp.status_code == 404
    assert cross_msg_resp.json()["detail"] == "Conversation not found."

    # 5. User 2 access to User 1's conversation detail returns 404
    cross_detail_resp = await async_client.get(
        f"/conversations/{conv_id}",
        headers=auth_headers_2,
    )
    assert cross_detail_resp.status_code == 404

    # 6. User 2 rename of User 1's conversation returns 404
    cross_patch_resp = await async_client.patch(
        f"/conversations/{conv_id}",
        headers=auth_headers_2,
        json={"title": "Hijacked Title"},
    )
    assert cross_patch_resp.status_code == 404

    # 7. User 2 deletion of User 1's conversation returns 404
    cross_del_resp = await async_client.delete(
        f"/conversations/{conv_id}",
        headers=auth_headers_2,
    )
    assert cross_del_resp.status_code == 404


@pytest.mark.asyncio
async def test_send_message_validation_and_no_followup_suggestions(
    async_client, db, test_user, auth_headers, auth_headers_2, mock_rag_service
):
    """Verify POST /conversations/{id}/messages validation, citation sources, and absence of suggestions."""
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="vid_contract_msg",
        user_id=test_user.id,
        status="processed",
    )

    c_resp = await async_client.post(
        "/conversations",
        headers=auth_headers,
        json={"title": "Contract Chat", "video_id": "vid_contract_msg"},
    )
    conv_id = c_resp.json()["id"]

    # 1. Empty message content rejected with 400
    empty_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "   "},
    )
    assert empty_resp.status_code == 400
    assert "message content or question is required" in empty_resp.json()["detail"].lower()

    # 2. Send message to non-existent conversation returns 404
    notfound_resp = await async_client.post(
        "/conversations/999999/messages",
        headers=auth_headers,
        json={"content": "Hello?"},
    )
    assert notfound_resp.status_code == 404

    # 3. User 2 sending message to User 1's conversation returns 404
    cross_send_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers_2,
        json={"content": "Intruder question"},
    )
    assert cross_send_resp.status_code == 404

    # 4. Valid message returns citations (sources) but NO follow-up suggestions
    valid_resp = await async_client.post(
        f"/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "What is covered in this video?"},
    )
    assert valid_resp.status_code == 200
    data = valid_resp.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) > 0
    # Confirm contract: no suggestions or follow_up fields
    assert "suggestions" not in data
    assert "follow_up_questions" not in data


@pytest.mark.asyncio
async def test_ask_endpoint_citations_and_no_followup_suggestions(
    async_client, db, test_user, auth_headers, mock_rag_service
):
    """Verify POST /ask returns citations (sources) and NO follow-up suggestions."""
    storage = VideoStorageService(db)
    storage.create_or_update_video(
        video_id="vid_contract_ask",
        user_id=test_user.id,
        status="processed",
    )

    resp = await async_client.post(
        "/ask",
        headers=auth_headers,
        json={
            "video_id": "vid_contract_ask",
            "question": "What is the key takeaway?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) > 0
    # Sources must have start_time, end_time, start_time_formatted, end_time_formatted, url, score
    src = data["sources"][0]
    assert "start_time" in src
    assert "end_time" in src
    assert "url" in src
    assert "score" in src
    # Confirm contract: no suggestions or follow_up fields
    assert "suggestions" not in data
    assert "follow_up_questions" not in data


@pytest.mark.asyncio
async def test_error_handling_consistency_and_no_leakage(async_client):
    """Verify standard status codes (404, 405) and ensure error responses do not leak traces or secrets."""
    # 1. Unsupported method -> 405 Method Not Allowed
    method_resp = await async_client.post("/health")
    assert method_resp.status_code == 405
    assert method_resp.json()["detail"] == "Method Not Allowed"

    # 2. Non-existent path -> 404 Not Found
    not_found_resp = await async_client.get("/api/v2/nonexistent/route")
    assert not_found_resp.status_code == 404
    assert not_found_resp.json()["detail"] == "Not Found"

    # 3. Check error response structure
    detail_str = str(not_found_resp.json())
    assert "Traceback" not in detail_str
    assert "password" not in detail_str.lower()
    assert "secret" not in detail_str.lower()
