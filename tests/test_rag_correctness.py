import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService


# ----------------------------------------------------
# 1. Test Citation Persistence & Reloading across APIs
# ----------------------------------------------------

@pytest.mark.asyncio
async def test_citation_persistence_and_reloading(async_client, auth_headers, db, test_user):
    # Create conversation
    conv = Conversation(user_id=test_user.id, title="Test Citations Conversation", video_id="test_vid_cite")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    service = ConversationService()
    citation_data = [
        {"text": "Relevant segment text from video", "start": 42.5, "duration": 8.0, "url": "https://youtu.be/test_vid_cite?t=42"},
    ]

    # Save user message and assistant message with citations
    service.add_message(db=db, conversation_id=conv.id, role="user", content="What happened at 42 seconds?")
    service.add_message(
        db=db,
        conversation_id=conv.id,
        role="assistant",
        content="The speaker explained the architecture at 42 seconds.",
        citations=citation_data,
    )

    # 1. Fetch via GET /conversations/{id}
    res1 = await async_client.get(f"/conversations/{conv.id}", headers=auth_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["messages"]) == 2
    user_msg = data1["messages"][0]
    asst_msg = data1["messages"][1]
    assert user_msg["role"] == "user"
    assert user_msg["sources"] == []
    assert asst_msg["role"] == "assistant"
    assert len(asst_msg["sources"]) == 1
    assert asst_msg["sources"][0]["start"] == 42.5

    # 2. Fetch via GET /conversations/{id}/messages
    res2 = await async_client.get(f"/conversations/{conv.id}/messages", headers=auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["messages"]) == 2
    asst_msg_page = [m for m in data2["messages"] if m["role"] == "assistant"][0]
    assert len(asst_msg_page["sources"]) == 1
    assert asst_msg_page["sources"][0]["text"] == "Relevant segment text from video"


# ----------------------------------------------------
# 2. Test LLM JSON Code Fence Stripping & Fallbacks
# ----------------------------------------------------

def test_llm_markdown_code_fence_stripping():
    with patch.dict("os.environ", {"GROQ_API_KEY": "dummy_key"}):
        llm = LLMService()

    # Case A: ```json ... ``` code fence
    mock_choice_a = MagicMock()
    mock_choice_a.message.content = "```json\n{\"answer\": \"Fence stripped\", \"sources\": [{\"text\": \"s1\"}]}\n```"
    llm.client.chat.completions.create = MagicMock(return_value=MagicMock(choices=[mock_choice_a]))

    res_a = llm.answer_question("What is X?", "Context chunk")
    assert res_a["answer"] == "Fence stripped"
    assert len(res_a["sources"]) == 1

    # Case B: ``` ... ``` code fence without json tag
    mock_choice_b = MagicMock()
    mock_choice_b.message.content = "```\n{\"answer\": \"Raw fence stripped\", \"sources\": []}\n```"
    llm.client.chat.completions.create = MagicMock(return_value=MagicMock(choices=[mock_choice_b]))

    res_b = llm.answer_question("What is X?", "Context chunk")
    assert res_b["answer"] == "Raw fence stripped"
    assert res_b["sources"] == []

    # Case C: Preamble and postamble around JSON
    mock_choice_c = MagicMock()
    mock_choice_c.message.content = "Here is the JSON answer you requested:\n{\"answer\": \"Extracted from text\", \"sources\": []}\nHope that helps!"
    llm.client.chat.completions.create = MagicMock(return_value=MagicMock(choices=[mock_choice_c]))

    res_c = llm.answer_question("What is X?", "Context chunk")
    assert res_c["answer"] == "Extracted from text"

    # Case D: Malformed text that cannot be parsed as JSON
    mock_choice_d = MagicMock()
    mock_choice_d.message.content = "This is pure unformatted plain text with no JSON structure."
    llm.client.chat.completions.create = MagicMock(return_value=MagicMock(choices=[mock_choice_d]))

    res_d = llm.answer_question("What is X?", "Context chunk")
    assert res_d["answer"] == LLMService.NOT_FOUND_MESSAGE
    assert res_d["sources"] == []


# ----------------------------------------------------
# 3. Test GROQ_MODEL Configuration Usage
# ----------------------------------------------------

def test_llm_service_uses_groq_model_setting():
    with patch.dict("os.environ", {"GROQ_API_KEY": "dummy_key"}):
        llm = LLMService()

    assert llm.model == settings.GROQ_MODEL

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="{\"answer\": \"ok\", \"sources\": []}"))]
    llm.client.chat.completions.create = MagicMock(return_value=mock_resp)

    llm.answer_question("Question", "Context")
    call_kwargs = llm.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == settings.GROQ_MODEL


# ----------------------------------------------------
# 4. Test Cache Preference Isolation in RAG
# ----------------------------------------------------

def test_cache_preference_isolation(db):
    from app.services.cache_service import CacheService

    cache = CacheService(db)
    key_concise = cache.save_answer(
        video_id="pref_vid",
        question="How does X work?",
        answer="Short answer.",
        sources=[],
        answer_length="concise",
        response_style="bullet_points",
    )

    key_detailed = cache.save_answer(
        video_id="pref_vid",
        question="How does X work?",
        answer="Comprehensive explanation with extensive background.",
        sources=[],
        answer_length="detailed",
        response_style="explanatory",
    )

    # Distinct keys
    assert key_concise != key_detailed

    # Retrieving concise does not return detailed
    ans_concise = cache.get_cached_answer(
        video_id="pref_vid",
        question="How does X work?",
        answer_length="concise",
        response_style="bullet_points",
    )
    assert ans_concise is not None
    assert ans_concise["answer"] == "Short answer."

    ans_detailed = cache.get_cached_answer(
        video_id="pref_vid",
        question="How does X work?",
        answer_length="detailed",
        response_style="explanatory",
    )
    assert ans_detailed is not None
    assert ans_detailed["answer"] == "Comprehensive explanation with extensive background."
