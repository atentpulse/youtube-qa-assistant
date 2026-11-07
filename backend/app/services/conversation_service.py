from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql import func

from app.models.conversation import (
    Conversation,
)

from app.models.message import (
    Message,
)


class ConversationService:

    # --------------------------------
    # Create conversation
    # --------------------------------

    def create_conversation(
        self,
        db: Session,
        user_id: int,
        title: str | None = None,
        video_id: str | None = None,
    ) -> Conversation:

        conversation = Conversation(
            user_id=user_id,
            title=title,
            video_id=video_id,
        )

        db.add(
            conversation
        )

        db.commit()

        db.refresh(
            conversation
        )

        return conversation


    # --------------------------------
    # Get user's conversations
    # --------------------------------

    def get_user_conversations(
        self,
        db: Session,
        user_id: int,
        video_id: str | None = None,
    ) -> list[Conversation]:

        query = (
            db.query(Conversation)
            .options(
                joinedload(Conversation.video),
                selectinload(Conversation.messages),
            )
            .filter(
                Conversation.user_id == user_id
            )
        )

        if video_id:
            query = query.filter(
                Conversation.video_id == video_id
            )

        conversations = (
            query
            .order_by(
                Conversation.updated_at.desc()
            )
            .all()
        )

        return conversations


    # --------------------------------
    # Get single conversation
    # --------------------------------

    def get_conversation(
        self,
        db: Session,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

        return conversation


    # --------------------------------
    # Add message
    # --------------------------------

    def add_message(
        self,
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        citations: str | list[dict] | None = None,
    ) -> Message:
        import json

        citations_str = None
        if citations is not None:
            if isinstance(citations, (list, dict)):
                citations_str = json.dumps(citations)
            else:
                citations_str = str(citations)

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations_str,
        )

        db.add(
            message
        )

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id
            )
            .first()
        )

        if conversation:

            conversation.updated_at = func.now()

        db.commit()

        db.refresh(
            message
        )

        return message
    
    # --------------------------------
    # Delete conversation
    # --------------------------------

    def delete_conversation(
        self,
        db: Session,
        conversation_id: int,
        user_id: int,
    ) -> bool:

        conversation = (
            self.get_conversation(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )

        if conversation is None:

            return False

        db.delete(
            conversation
        )

        db.commit()

        return True
    
    # --------------------------------
    # Generate conversation title
    # --------------------------------

    def generate_title(
        self,
        question: str,
    ) -> str:

        words = question.strip().split()

        title_words = words[:6]

        title = " ".join(
            title_words
        )

        return title
    
    # --------------------------------
    # Update conversation title
    # --------------------------------

    def update_title(
        self,
        db: Session,
        conversation_id: int,
        title: str,
    ) -> Conversation | None:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id
            )
            .first()
        )

        if conversation is None:

            return None

        conversation.title = title

        db.commit()

        db.refresh(
            conversation
        )

        return conversation
    
    # --------------------------------
    # Update conversation title
    # --------------------------------

    def update_conversation_title(
        self,
        db: Session,
        conversation_id: int,
        user_id: int,
        title: str,
    ) -> Conversation | None:

        conversation = (
            self.get_conversation(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )

        if conversation is None:

            return None

        conversation.title = title.strip()

        db.commit()

        db.refresh(
            conversation
        )

        return conversation
    
    # --------------------------------
    # Get paginated messages
    # --------------------------------

    def get_messages(
        self,
        db: Session,
        conversation_id: int,
        user_id: int,
        limit: int = 20,
        before_id: int | None = None,
    ) -> list[Message] | None:

        # Verify conversation ownership
        conversation = (
            self.get_conversation(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )

        if conversation is None:

            return None


        query = (
            db.query(Message)
            .filter(
                Message.conversation_id
                == conversation_id
            )
        )


        # Load messages older than before_id
        if before_id is not None:

            query = query.filter(
                Message.id < before_id
            )


        # Get newest messages first
        messages = (
            query
            .order_by(
                Message.id.desc()
            )
            .limit(limit)
            .all()
        )


        # Reverse for normal chat display
        messages.reverse()


        return messages
    
    # --------------------------------
    # Get recent conversation messages
    # --------------------------------

    def get_recent_messages(
        self,
        db: Session,
        conversation_id: int,
        limit: int = 6,
    ) -> list[Message]:

        messages = (
            db.query(Message)
            .filter(
                Message.conversation_id
                == conversation_id
            )
            .order_by(
                Message.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        # Reverse to chronological order
        messages.reverse()

        return messages