from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.auth.dependencies import (
    get_current_user,
)

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

from app.schemas.conversation import (
    CreateConversationRequest,
    ConversationResponse,
    ConversationDetailResponse,
    UpdateConversationRequest,
    PaginatedMessagesResponse,
    SendMessageRequest,
    SendMessageResponse,
)

from app.services.conversation_service import (
    ConversationService,
)

from app.services.rag_service import (
    RAGService,
)
from app.dependencies import get_rag_service


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


conversation_service = ConversationService()


# --------------------------------
# Create conversation
# --------------------------------

@router.post(
    "",
    response_model=ConversationResponse,
)
def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    conversation = (
        conversation_service.create_conversation(
            db=db,
            user_id=current_user.id,
            title=request.title,
            video_id=request.video_id,
        )
    )

    return conversation


# --------------------------------
# Get user conversations
# --------------------------------

@router.get(
    "",
    response_model=list[ConversationResponse],
)
def get_conversations(
    video_id: str | None = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    return (
        conversation_service.get_user_conversations(
            db=db,
            user_id=current_user.id,
            video_id=video_id,
        )
    )


# --------------------------------
# Export conversation history
# --------------------------------

@router.get(
    "/export",
)
def export_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_conversations = conversation_service.get_user_conversations(
        db=db,
        user_id=current_user.id,
    )

    export_data = {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        },
        "total_conversations": len(user_conversations),
        "conversations": [],
    }

    for conv in user_conversations:
        messages = conversation_service.get_messages(
            db=db,
            conversation_id=conv.id,
            user_id=current_user.id,
            limit=1000,
        )
        export_data["conversations"].append({
            "id": conv.id,
            "title": conv.title,
            "video_id": conv.video_id,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in (messages or [])
            ],
        })

    return export_data


# --------------------------------
# Clear all conversations
# --------------------------------

@router.delete(
    "",
)
def clear_all_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .delete(synchronize_session="fetch")
    )
    db.commit()

    return {
        "message": f"Successfully cleared {count} conversations.",
        "cleared_count": count,
    }


# --------------------------------
# Get paginated conversation messages
# IMPORTANT: This route must come BEFORE
# /{conversation_id}
# --------------------------------

@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedMessagesResponse,
)
def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    before_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    messages = (
        conversation_service.get_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=limit,
            before_id=before_id,
        )
    )

    if messages is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    next_cursor = None

    if messages:

        oldest_message_id = messages[0].id

        older_message_exists = (
            db.query(Message)
            .filter(
                Message.conversation_id
                == conversation_id,
                Message.id < oldest_message_id,
            )
            .first()
        )

        if older_message_exists:

            next_cursor = oldest_message_id

    return {
        "messages": messages,
        "next_cursor": next_cursor,
    }


# --------------------------------
# Send message in conversation (RESTful endpoint)
# --------------------------------

@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
def send_conversation_message(
    conversation_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
    rag_service: RAGService = Depends(
        get_rag_service
    ),
):

    question_text = request.content or request.question

    if not question_text or not question_text.strip():

        raise HTTPException(
            status_code=400,
            detail="Message content or question is required.",
        )

    question_text = question_text.strip()

    # 1. Verify conversation ownership
    conversation = conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    # 2. Determine target video ID
    target_video_id = request.video_id or conversation.video_id

    if not target_video_id:

        raise HTTPException(
            status_code=400,
            detail="video_id must be provided or bound to this conversation.",
        )

    target_video_id = target_video_id.strip()

    # 3. Check cross-video leakage
    if conversation.video_id and conversation.video_id != target_video_id:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Conversation is bound to video '{conversation.video_id}', "
                f"cannot send messages for '{target_video_id}'."
            ),
        )

    if not conversation.video_id:

        conversation.video_id = target_video_id
        db.commit()

    # 4. Generate title if missing
    if not conversation.title:

        title = conversation_service.generate_title(question_text)
        conversation_service.update_title(
            db=db,
            conversation_id=conversation.id,
            title=title,
        )

    # 5. Build conversation context
    recent_messages = conversation_service.get_recent_messages(
        db=db,
        conversation_id=conversation.id,
        limit=6,
    )

    conversation_context = ""
    for message in recent_messages:
        conversation_context += f"{message.role.capitalize()}: {message.content}\n"

    rewrite_context = ""
    for message in recent_messages:
        if message.role == "user":
            rewrite_context += f"User: {message.content}\n"

    # 6. Execute RAG
    try:
        try:
            rag_result = rag_service.ask_question(
                db=db,
                user_id=current_user.id,
                video_id=target_video_id,
                question=question_text,
                conversation_context=conversation_context,
                rewrite_context=rewrite_context,
                answer_length=request.answer_length or "balanced",
                response_style=request.response_style or "explanatory",
                prefer_structured=request.prefer_structured if request.prefer_structured is not None else True,
                include_examples=bool(request.include_examples),
            )
        except TypeError as type_err:
            if "unexpected keyword argument" in str(type_err):
                rag_result = rag_service.ask_question(
                    db=db,
                    user_id=current_user.id,
                    video_id=target_video_id,
                    question=question_text,
                    conversation_context=conversation_context,
                    rewrite_context=rewrite_context,
                )
            else:
                raise

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    # 7. Persist user message
    conversation_service.add_message(
        db=db,
        conversation_id=conversation.id,
        role="user",
        content=question_text,
    )

    # 8. Persist assistant message
    assistant_msg = conversation_service.add_message(
        db=db,
        conversation_id=conversation.id,
        role="assistant",
        content=rag_result["answer"],
    )

    return {
        "id": assistant_msg.id,
        "conversation_id": conversation.id,
        "role": "assistant",
        "content": rag_result["answer"],
        "sources": rag_result.get("sources", []),
        "created_at": assistant_msg.created_at,
    }


# --------------------------------
# Get conversation
# --------------------------------

@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    conversation = (
        conversation_service.get_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation


# --------------------------------
# Update conversation title
# --------------------------------

@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation_title(
    conversation_id: int,
    request: UpdateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    conversation = (
        conversation_service.update_conversation_title(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            title=request.title,
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation


# --------------------------------
# Delete conversation
# --------------------------------

@router.delete(
    "/{conversation_id}",
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    deleted = (
        conversation_service.delete_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return {
        "message": "Conversation deleted successfully."
    }
