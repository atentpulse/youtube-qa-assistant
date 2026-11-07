import hashlib
import json
from sqlalchemy.orm import Session

from app.models.question_cache import QuestionCache


class CacheService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_question(question: str) -> str:
        """Collapse multiple spaces and lowercase the question string."""
        return " ".join(question.strip().lower().split())

    @classmethod
    def compute_cache_key(
        cls,
        video_id: str,
        question: str,
        answer_length: str = "balanced",
        response_style: str = "explanatory",
        prefer_structured: bool = True,
        include_examples: bool = False,
        model_id: str = "default",
        prompt_version: str = "v1",
    ) -> str:
        """
        Deterministically compute a 64-character SHA-256 hash representing all answer-affecting inputs.
        Prevents Postgres btree index limits while guaranteeing strict answer isolation.
        """
        norm_q = cls._normalize_question(question)
        payload = json.dumps(
            {
                "video_id": str(video_id).strip(),
                "q": norm_q,
                "len": str(answer_length).strip().lower(),
                "style": str(response_style).strip().lower(),
                "struct": bool(prefer_structured),
                "ex": bool(include_examples),
                "model": str(model_id).strip().lower(),
                "v": str(prompt_version).strip().lower(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_cached_answer(
        self,
        video_id: str,
        question: str,
        answer_length: str = "balanced",
        response_style: str = "explanatory",
        prefer_structured: bool = True,
        include_examples: bool = False,
        model_id: str = "default",
        prompt_version: str = "v1",
    ):
        cache_key = self.compute_cache_key(
            video_id=video_id,
            question=question,
            answer_length=answer_length,
            response_style=response_style,
            prefer_structured=prefer_structured,
            include_examples=include_examples,
            model_id=model_id,
            prompt_version=prompt_version,
        )

        cache_entry = (
            self.db.query(QuestionCache)
            .filter(QuestionCache.cache_key == cache_key)
            .first()
        )

        if cache_entry is None:
            return None

        try:
            sources = json.loads(cache_entry.sources)
        except (json.JSONDecodeError, TypeError):
            sources = []

        return {
            "answer": cache_entry.answer,
            "sources": sources,
            "cache_key": cache_key,
        }

    def save_answer(
        self,
        video_id: str,
        question: str,
        answer: str,
        sources: list,
        answer_length: str = "balanced",
        response_style: str = "explanatory",
        prefer_structured: bool = True,
        include_examples: bool = False,
        model_id: str = "default",
        prompt_version: str = "v1",
    ) -> str:
        cache_key = self.compute_cache_key(
            video_id=video_id,
            question=question,
            answer_length=answer_length,
            response_style=response_style,
            prefer_structured=prefer_structured,
            include_examples=include_examples,
            model_id=model_id,
            prompt_version=prompt_version,
        )
        sources_json = json.dumps(sources)

        bind = self.db.get_bind()
        dialect_name = bind.dialect.name if bind is not None else "postgresql"

        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(QuestionCache).values(
                cache_key=cache_key,
                video_id=video_id,
                question=question,
                answer=answer,
                sources=sources_json,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["cache_key"],
                set_={
                    "answer": stmt.excluded.answer,
                    "sources": stmt.excluded.sources,
                    "question": stmt.excluded.question,
                },
            )
            self.db.execute(stmt)
            self.db.commit()
        elif dialect_name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            stmt = sqlite_insert(QuestionCache).values(
                cache_key=cache_key,
                video_id=video_id,
                question=question,
                answer=answer,
                sources=sources_json,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["cache_key"],
                set_={
                    "answer": stmt.excluded.answer,
                    "sources": stmt.excluded.sources,
                    "question": stmt.excluded.question,
                },
            )
            self.db.execute(stmt)
            self.db.commit()
        else:
            entry = self.db.query(QuestionCache).filter_by(cache_key=cache_key).first()
            if entry:
                entry.answer = answer
                entry.sources = sources_json
                entry.question = question
            else:
                entry = QuestionCache(
                    cache_key=cache_key,
                    video_id=video_id,
                    question=question,
                    answer=answer,
                    sources=sources_json,
                )
                self.db.add(entry)
            self.db.commit()

        return cache_key

    def delete_cached_answer(
        self,
        video_id: str,
        question: str,
        answer_length: str = "balanced",
        response_style: str = "explanatory",
        prefer_structured: bool = True,
        include_examples: bool = False,
        model_id: str = "default",
        prompt_version: str = "v1",
    ) -> bool:
        cache_key = self.compute_cache_key(
            video_id=video_id,
            question=question,
            answer_length=answer_length,
            response_style=response_style,
            prefer_structured=prefer_structured,
            include_examples=include_examples,
            model_id=model_id,
            prompt_version=prompt_version,
        )
        deleted_count = (
            self.db.query(QuestionCache)
            .filter(QuestionCache.cache_key == cache_key)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted_count > 0

    def delete_video_cache(self, video_id: str) -> int:
        deleted_count = (
            self.db.query(QuestionCache)
            .filter(QuestionCache.video_id == video_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted_count
