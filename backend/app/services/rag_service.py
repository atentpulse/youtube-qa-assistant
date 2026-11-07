from app.services.youtube_service import (
    extract_video_id,
    fetch_video_metadata,
    fetch_transcript,
    format_transcript,
)

from app.services.video_storage_service import (
    VideoStorageService,
)

from app.database.database import SessionLocal

from app.services.chunking_service import (
    create_chunks,
)

from app.utils.time_utils import (
    format_timestamp,
    create_youtube_timestamp_url,
)

from app.services.embedding_service import (
    EmbeddingService,
)

from app.services.qdrant_service import (
    QdrantVectorStore,
)

from app.services.llm_service import (
    LLMService,
)

from app.services.cache_service import (
    CacheService,
)

from app.services.reranker_service import (
    RerankerService,
)

from app.services.lock_service import (
    VideoIngestionLock,
)

import logging
import threading
import time

logger = logging.getLogger(__name__)


class RAGService:

    def __init__(self):

        self.embedding_service = EmbeddingService()

        self.vector_store = QdrantVectorStore()

        self.llm_service = LLMService()

        self.reranker_service = RerankerService()

        self._in_flight_videos: set[str] = set()
        self._in_flight_lock = threading.Lock()

        self.vector_store.create_collection(
            vector_size=384
        )

    def process_video(
    self,
    db,
    user_id: int,
    url: str,
    force_reprocess: bool = False,
    ):

        # --------------------------------
        # 1. Extract video ID
        # --------------------------------

        video_id = extract_video_id(url)

        video_storage = VideoStorageService(db)
        try:
            video_storage.recover_stale_jobs(max_age_minutes=15)
        except Exception as stale_err:
            logger.warning("Failed to recover stale jobs: %s", stale_err)

        # --------------------------------
        # 2. Check in-flight processing lock
        # --------------------------------

        with self._in_flight_lock:
            is_in_flight = video_id in self._in_flight_videos

        if is_in_flight or VideoIngestionLock.is_locked(db, video_id):
            video_storage.link_user_to_video(
                user_id=user_id,
                video_id=video_id,
            )
            return {
                "video_id": video_id,
                "segments": 0,
                "chunks": 0,
                "status": "already_processing",
            }

        # --------------------------------
        # 3. Check canonical video
        # --------------------------------

        canonical_video = video_storage.get_canonical_video(
            video_id=video_id,
        )

        if canonical_video:
            video_storage.link_user_to_video(
                user_id=user_id,
                video_id=video_id,
            )

            if (
                canonical_video["status"] == "processed"
                and not force_reprocess
            ):
                return {
                    "video_id": video_id,
                    "segments": canonical_video["segments"],
                    "chunks": canonical_video["chunks"],
                    "status": "already_processed",
                }

            if canonical_video["status"] == "processing":
                return {
                    "video_id": video_id,
                    "segments": canonical_video["segments"],
                    "chunks": canonical_video["chunks"],
                    "status": "already_processing",
                }

        # --------------------------------
        # 4. Fetch video metadata
        # --------------------------------

        metadata = fetch_video_metadata(video_id)

        # --------------------------------
        # 5. Acquire in-flight lock & mark processing
        # --------------------------------

        with self._in_flight_lock:
            self._in_flight_videos.add(video_id)

        video_storage.create_or_update_video(
            video_id=video_id,
            user_id=user_id,
            title=metadata["title"],
            thumbnail_url=metadata["thumbnail_url"],
            status="processing",
        )

        return {
            "video_id": video_id,
            "segments": 0,
            "chunks": 0,
            "status": "processing",
        }

    def process_video_background(
    self,
    video_id: str,
    user_id: int,
    ):

        db = SessionLocal()
        lock = VideoIngestionLock(db, video_id)
        if not lock.acquire():
            print(
                f"Video {video_id} is already being ingested by another process or worker; skipping background task."
            )
            db.close()
            return

        try:

            video_storage = VideoStorageService(db)
            cache_service = CacheService(db)

            # --------------------------------
            # Fetch transcript
            # --------------------------------

            transcript = fetch_transcript(video_id)

            segments = format_transcript(
                transcript
            )

            # --------------------------------
            # Create chunks
            # --------------------------------

            chunks = create_chunks(
                segments,
                max_words=180,
            )

            chunk_texts = [
                chunk["text"]
                for chunk in chunks
            ]

            # --------------------------------
            # Create embeddings
            # --------------------------------

            embeddings = (
                self.embedding_service.embed_documents(
                    chunk_texts
                )
            )

            # --------------------------------
            # Add video ID
            # --------------------------------

            for chunk in chunks:

                chunk["video_id"] = video_id

            # --------------------------------
            # Remove old vectors
            # --------------------------------

            if self.vector_store.video_exists(
                video_id
            ):

                self.vector_store.delete_video(
                    video_id
                )

            # --------------------------------
            # Clear old cached answers
            # --------------------------------

            cache_service.delete_video_cache(video_id)

            # --------------------------------
            # Store vectors
            # --------------------------------

            self.vector_store.add_documents(
                embeddings=embeddings,
                chunks=chunks,
            )

            # --------------------------------
            # Mark processed
            # --------------------------------

            video_storage.create_or_update_video(
                video_id=video_id,
                user_id=user_id,
                status="processed",
                segments=len(segments),
                chunks=len(chunks),
            )

            print(
                f"Video processed successfully: "
                f"{video_id}"
            )

        except Exception as error:

            logger.error(
                "Video processing failed for %s: %s",
                video_id,
                error,
                exc_info=True,
            )
            print(
                f"Video processing failed: "
                f"{error}"
            )

            # Clean partial vectors safely
            try:
                if self.vector_store.video_exists(
                    video_id
                ):
                    self.vector_store.delete_video(
                        video_id
                    )
            except Exception as clean_err:
                logger.warning(
                    "Failed to clean partial vectors for %s: %s",
                    video_id,
                    clean_err,
                )

            # Mark failed in DB safely
            try:
                video_storage.create_or_update_video(
                    video_id=video_id,
                    user_id=user_id,
                    status="failed",
                    error_message=str(error)[:1000],
                )
            except Exception as db_err:
                logger.error(
                    "Failed to mark video %s as failed in database: %s",
                    video_id,
                    db_err,
                )

        finally:

            with self._in_flight_lock:
                self._in_flight_videos.discard(video_id)

            lock.release()
            db.close()

    def ask_question(
        self,
        db,
        user_id: int,
        video_id: str,
        question: str,
        conversation_context: str = "",
        rewrite_context: str = "",
        top_k: int = 15,
        answer_length: str = "balanced",
        response_style: str = "explanatory",
        prefer_structured: bool = True,
        include_examples: bool = False,
    ):

        # --------------------------------
        # 1. Check video metadata
        # --------------------------------

        video_storage = VideoStorageService(db)

        video = video_storage.get_video(
            video_id=video_id,
            user_id=user_id,
        )
        
        cache_service = CacheService(db)

        if video is None:

            raise ValueError(
                "This video has not been processed yet. "
                "Please process the video first."
            )

        if video["status"] == "processing":

            raise ValueError(
                "This video is currently being processed. " "Please try again shortly."
            )

        if video["status"] == "failed":

            raise ValueError(
                "Video processing failed. " "Please process the video again."
            )

        if video["status"] != "processed":

            raise ValueError(
                f"Video is not ready. " f"Current status: {video['status']}"
            )

        # --------------------------------
        # 2. Check answer cache
        # --------------------------------

        not_found_message = "I could not find the answer " "in the video transcript."

        # Only use cache when there is no
        # conversation context
        if not conversation_context.strip():

            cached_answer = cache_service.get_cached_answer(
    video_id=video_id,
    question=question,
)

            if cached_answer:

                if cached_answer["answer"].strip() == not_found_message:

                    # Remove old bad cache entry
                    cache_service.delete_cached_answer(
    video_id=video_id,
    question=question,
)

                    print("Removed old not-found cache entry.")

                else:

                    print("Answer returned from cache!")

                    return cached_answer

        # --------------------------------
        # Start total timer
        # --------------------------------

        total_start = time.perf_counter()

        # --------------------------------
        # Build retrieval query
        # --------------------------------

        retrieval_query = question

        if rewrite_context.strip() and self.llm_service.needs_question_rewrite(
            question
        ):
            retrieval_query = self.llm_service.rewrite_question(
                question=question,
                conversation_context=rewrite_context,
            )
            print("Question rewritten for retrieval.")
        else:
            print("Original question used for retrieval.")

        print(f"\nRetrieval query: " f"{retrieval_query}\n")

        # --------------------------------
        # 3. Embed question
        # --------------------------------

        embedding_start = time.perf_counter()

        query_embedding = self.embedding_service.embed_query(retrieval_query)[0]

        embedding_time = time.perf_counter() - embedding_start

        # --------------------------------
        # 4. Search Qdrant
        # --------------------------------

        search_start = time.perf_counter()

        results = self.vector_store.search(
            query_embedding=query_embedding,
            video_id=video_id,
            top_k=top_k,
        )
        print("\n--- RETRIEVED CONTEXT ---")

        for index, result in enumerate(results, start=1):
            print(f"\nRESULT {index}")
            print(f"Score: {result['score']:.4f}")
            print(f"Text: {result['text'][:500]}")

        print("\n-------------------------\n")

        search_time = time.perf_counter() - search_start

        # --------------------------------
        # 5. Filter and rerank results
        # --------------------------------

        # Keep the strongest Qdrant candidates for reranking.
        # The CrossEncoder will perform the final relevance ranking.
        relevant_results = results[:15]

        reranker_start = time.perf_counter()

        reranked_results = self.reranker_service.rerank(
            question=retrieval_query,
            results=relevant_results,
            top_k=5,
        )

        reranker_time = time.perf_counter() - reranker_start

        print("\n--- RERANKING RESULTS ---")

        for index, result in enumerate(
            reranked_results,
            start=1,
        ):
            print(f"\nResult {index}")

            print(f"Qdrant score: " f"{result['score']:.4f}")

            print(f"Rerank score: " f"{result['rerank_score']:.4f}")

            print(f"Text: " f"{result['text'][:300]}")

        print("\n-------------------------\n")

        answer_results = reranked_results

        if not answer_results:

            total_time = time.perf_counter() - total_start

            print("\n--- RAG PERFORMANCE ---")

            print(f"Embedding: {embedding_time:.3f}s")

            print(f"Qdrant:    {search_time:.3f}s")

            print(f"Reranker:  {reranker_time:.3f}s")

            print("LLM:       0.000s")

            print(f"Total:     {total_time:.3f}s")

            print("-----------------------\n")

            return {
                "answer": not_found_message,
                "sources": [],
            }

        # --------------------------------
        # 6. Build context
        # --------------------------------

        context_parts = []

        for index, result in enumerate(
            answer_results,
            start=1,
        ):

            context_parts.append(f"""
        [SOURCE {index}]

        Timestamp:
        {result["start_time"]:.2f}s
        to
        {result["end_time"]:.2f}s

        Transcript:
        {result["text"]}
        """)

        context = "\n\n".join(context_parts)

        # --------------------------------
        # 7. Generate answer
        # --------------------------------

        llm_start = time.perf_counter()

        llm_result = self.llm_service.answer_question(
            question=question,
            context=context,
            conversation_context=conversation_context,
            answer_length=answer_length,
            response_style=response_style,
            prefer_structured=prefer_structured,
            include_examples=include_examples,
        )

        answer = llm_result["answer"]

        used_source_numbers = llm_result["sources"]

        llm_time = time.perf_counter() - llm_start

        # --------------------------------
        # Check if LLM found an answer
        # --------------------------------

        not_found_message = "I could not find the answer " "in the video transcript."
        if answer.strip() == not_found_message:

            total_time = time.perf_counter() - total_start

            print("\n--- RAG PERFORMANCE ---")
            print(f"Embedding: {embedding_time:.3f}s")
            print(f"Qdrant:    {search_time:.3f}s")

            print(f"Reranker:  {reranker_time:.3f}s")

            print(f"LLM:       {llm_time:.3f}s")
            print(f"Total:     {total_time:.3f}s")
            print("-----------------------\n")

            return {
                "answer": not_found_message,
                "sources": [],
            }

        # --------------------------------
        # 8. Build sources
        # --------------------------------

        sources = []

        # --------------------------------
        # Select only sources used by LLM
        # --------------------------------

        source_results = []

        for source_number in used_source_numbers:

            if not isinstance(
                source_number,
                int,
            ):
                continue

            # SOURCE numbers start at 1
            # Python indexes start at 0
            index = source_number - 1

            if 0 <= index < len(answer_results):

                source_results.append(answer_results[index])

        # --------------------------------
        # Build source response
        # --------------------------------

        for result in source_results:

            sources.append(
                {
                    "start_time": (result["start_time"]),
                    "end_time": (result["end_time"]),
                    "start_time_formatted": (format_timestamp(result["start_time"])),
                    "end_time_formatted": (format_timestamp(result["end_time"])),
                    "url": (
                        create_youtube_timestamp_url(
                            video_id=video_id,
                            seconds=result["start_time"],
                        )
                    ),
                    "score": result["score"],
                    "text": result.get("text", ""),
                }
            )

        # Deduplicate sources by timestamp and sort chronologically
        seen_timestamps = set()
        deduped_sources = []
        for src in sorted(sources, key=lambda s: s["start_time"]):
            key = round(src["start_time"] / 2.0)
            if key not in seen_timestamps:
                seen_timestamps.add(key)
                deduped_sources.append(src)
        sources = deduped_sources

        # Strip any accidental trailing "Sources: 1, 2" or "(Sources: ...)" from LLM answer
        import re
        answer = re.sub(r'(?i)\s*\(?sources:\s*[\d,\s]+\)?\s*$', '', answer).strip()
        answer = re.sub(r'(?i)\n+sources:\s*[\d,\s]+$', '', answer).strip()

        # --------------------------------
        # 9. Save answer to cache
        # --------------------------------

        # Only cache standalone questions
        if not conversation_context.strip():

            cache_service.save_answer(
    video_id=video_id,
    question=question,
    answer=answer,
    sources=sources,
)

        # --------------------------------
        # 10. Print performance
        # --------------------------------

        total_time = time.perf_counter() - total_start

        print("\n--- RAG PERFORMANCE ---")

        print(f"Embedding: {embedding_time:.3f}s")

        print(f"Qdrant:    {search_time:.3f}s")

        print(f"Reranker:  {reranker_time:.3f}s")

        print(f"LLM:       {llm_time:.3f}s")

        print(f"Total:     {total_time:.3f}s")

        print("-----------------------\n")

        # --------------------------------
        # 11. Return response
        # --------------------------------

        return {
            "answer": answer,
            "sources": sources,
        }

    def get_all_videos(
    self,
    db,
    user_id: int,
    limit: int = 10,
    offset: int = 0,
    status: str | None = None,
    ):

        video_storage = VideoStorageService(db)

        videos = video_storage.get_all_videos(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
        )

        total = video_storage.get_video_count(
            user_id=user_id,
            status=status,
        )

        return {
            "videos": videos,
            "total": total,
        }

    def update_video_metadata(
    self,
    db,
    user_id: int,
    video_id: str,
    ):

        video_storage = VideoStorageService(db)

        # --------------------------------
        # 1. Check video exists
        # --------------------------------

        video = video_storage.get_video(
            video_id=video_id,
            user_id=user_id,
        )

        if video is None:

            raise ValueError(
                "Video not found."
            )

        # --------------------------------
        # 2. Fetch YouTube metadata
        # --------------------------------

        metadata = fetch_video_metadata(
            video_id
        )

        # --------------------------------
        # 3. Update PostgreSQL metadata
        # --------------------------------

        video_storage.update_video_metadata(
            video_id=video_id,
            user_id=user_id,
            title=metadata["title"],
            thumbnail_url=metadata["thumbnail_url"],
        )

        return {
            "video_id": video_id,
            "title": metadata["title"],
            "thumbnail_url": metadata["thumbnail_url"],
            "status": "metadata_updated",
        }

    def delete_video(
    self,
    db,
    user_id: int,
    video_id: str,
    ):

        video_storage = VideoStorageService(db)
        cache_service = CacheService(db)

        # --------------------------------
        # 1. Check video ownership
        # --------------------------------

        video = video_storage.get_video(
            video_id=video_id,
            user_id=user_id,
        )

        if video is None:

            raise ValueError(
                "Video not found."
            )

        # --------------------------------
        # 2. Check if other references exist
        # --------------------------------

        has_other_refs = video_storage.has_other_references(
            video_id=video_id,
            exclude_user_id=user_id,
        )

        if not has_other_refs:

            # --------------------------------
            # Safe to delete vectors from Qdrant
            # --------------------------------

            self.vector_store.delete_video(
                video_id
            )

            # --------------------------------
            # Delete cached answers
            # --------------------------------

            cache_service.delete_video_cache(video_id)

        # --------------------------------
        # 3. Unlink/delete metadata from PostgreSQL
        # --------------------------------

        video_storage.delete_video(
            video_id=video_id,
            user_id=user_id,
        )

        return {
            "status": "deleted",
            "video_id": video_id,
        }
