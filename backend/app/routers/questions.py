from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.auth.dependencies import (
    get_current_user,
)
from app.models.user import User

from app.schemas.question import (
    AskQuestionRequest,
    AskQuestionResponse,
)

from app.services.rag_service import (
    RAGService,
)

from app.dependencies import get_rag_service

from app.services.conversation_service import (
    ConversationService,
)


router = APIRouter(
    tags=["Questions"],
)


conversation_service = ConversationService()


# --------------------------------
# Ask question
# --------------------------------

@router.post(
    "/ask",
    response_model=AskQuestionResponse,
)
def ask_question(
    request: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
    get_current_user
),
    rag_service: RAGService = Depends(
        get_rag_service
    ),
):

    try:

        # ----------------------------
        # Logged-in user
        # ----------------------------

        conversation = None


        # ----------------------------
        # Existing conversation
        # ----------------------------

        if request.conversation_id is not None:

            # ----------------------------
            # Verify conversation ownership
            # ----------------------------

            conversation = (
                conversation_service.get_conversation(
                    db=db,
                    conversation_id=request.conversation_id,
                    user_id=current_user.id,
                )
            )

            if conversation is None:

                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found.",
                )

            # ----------------------------
            # Verify video alignment
            # ----------------------------

            requested_video_id = request.video_id.strip()

            if conversation.video_id and conversation.video_id != requested_video_id:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Conversation is bound to video '{conversation.video_id}', "
                        f"cannot ask question for '{requested_video_id}'."
                    ),
                )

            if not conversation.video_id:

                conversation.video_id = requested_video_id
                db.commit()


            # ----------------------------
            # Generate title if missing
            # ----------------------------

            if not conversation.title:

                title = (
                    conversation_service.generate_title(
                        request.question
                    )
                )

                conversation_service.update_title(
                    db=db,
                    conversation_id=conversation.id,
                    title=title,
                )


        # ----------------------------
        # Get conversation history
        # ----------------------------

        recent_messages = []

        if conversation is not None:

            recent_messages = (
                conversation_service.get_recent_messages(
                    db=db,
                    conversation_id=conversation.id,
                    limit=6,
                )
            )


        # ----------------------------
        # Build conversation contexts
        # ----------------------------

        # Full history for the final LLM.
        #
        # This contains both user and assistant
        # messages so the final LLM can understand
        # the conversation flow.

        conversation_context = ""

        for message in recent_messages:

            conversation_context += (
                f"{message.role.capitalize()}: "
                f"{message.content}\n"
            )


        # User-only history for query rewriting.
        #
        # Previous assistant responses must NOT
        # influence retrieval because they may contain
        # hallucinated information.

        rewrite_context = ""

        for message in recent_messages:

            if message.role == "user":

                rewrite_context += (
                    f"User: "
                    f"{message.content}\n"
                )


        # ----------------------------
        # Generate RAG answer
        # ----------------------------

        result = rag_service.ask_question(
    db=db,
    user_id=current_user.id,
    video_id=request.video_id.strip(),
    question=request.question.strip(),
    conversation_context=conversation_context,
    rewrite_context=rewrite_context,
)


        # ----------------------------
        # Create new conversation
        # AFTER successful RAG
        # ----------------------------

        if conversation is None:

            title = (
                conversation_service.generate_title(
                    request.question
                )
            )

            conversation = (
                conversation_service.create_conversation(
                    db=db,
                    user_id=current_user.id,
                    title=title,
                    video_id=request.video_id.strip(),
                )
            )


        # ----------------------------
        # Save user question
        # ----------------------------

        conversation_service.add_message(
            db=db,
            conversation_id=conversation.id,
            role="user",
            content=request.question.strip(),
        )


        # ----------------------------
        # Save AI answer
        # ----------------------------

        conversation_service.add_message(
            db=db,
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
        )


        # ----------------------------
        # Return answer + conversation ID
        # ----------------------------

        return {
            **result,
            "conversation_id": conversation.id,
        }


    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )