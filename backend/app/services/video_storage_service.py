from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.user_video import UserVideo
from app.models.video import Video


class VideoStorageService:

    def __init__(self, db: Session):
        self.db = db

    def get_video(
        self,
        video_id: str,
        user_id: int,
    ):
        video = (
            self.db.query(Video)
            .filter(
                Video.video_id == video_id,
            )
            .first()
        )

        if video is None:
            return None

        user_link = (
            self.db.query(UserVideo)
            .filter(
                UserVideo.video_id == video_id,
                UserVideo.user_id == user_id,
            )
            .first()
        )

        # Backward compatibility for legacy rows before migration backfill
        if user_link is None and video.user_id != user_id:
            return None

        return self._to_dict(video)

    def get_canonical_video(
        self,
        video_id: str,
    ):
        video = (
            self.db.query(Video)
            .filter(
                Video.video_id == video_id,
            )
            .first()
        )

        if video is None:
            return None

        return self._to_dict(video)

    def create_or_update_video(
        self,
        video_id: str,
        user_id: int | None,
        status: str,
        segments: int = 0,
        chunks: int = 0,
        title: str | None = None,
        thumbnail_url: str | None = None,
    ):
        video = (
            self.db.query(Video)
            .filter(
                Video.video_id == video_id,
            )
            .first()
        )

        if video is None:
            video = Video(
                video_id=video_id,
                user_id=user_id,
                title=title,
                thumbnail_url=thumbnail_url,
                status=status,
                segments=segments,
                chunks=chunks,
            )
            self.db.add(video)
        else:
            if title is not None:
                video.title = title

            if thumbnail_url is not None:
                video.thumbnail_url = thumbnail_url

            video.status = status
            if segments:
                video.segments = segments
            if chunks:
                video.chunks = chunks
            video.updated_at = datetime.now(timezone.utc)

        if user_id is not None:
            user_link = (
                self.db.query(UserVideo)
                .filter(
                    UserVideo.video_id == video_id,
                    UserVideo.user_id == user_id,
                )
                .first()
            )

            if user_link is None:
                user_link = UserVideo(
                    user_id=user_id,
                    video_id=video_id,
                )
                self.db.add(user_link)

        self.db.commit()
        self.db.refresh(video)

        return self._to_dict(video)

    def link_user_to_video(
        self,
        user_id: int,
        video_id: str,
    ) -> bool:
        user_link = (
            self.db.query(UserVideo)
            .filter(
                UserVideo.video_id == video_id,
                UserVideo.user_id == user_id,
            )
            .first()
        )

        if user_link is None:
            user_link = UserVideo(
                user_id=user_id,
                video_id=video_id,
            )
            self.db.add(user_link)
            self.db.commit()

        return True

    def unlink_user_from_video(
        self,
        user_id: int,
        video_id: str,
    ) -> bool:
        user_link = (
            self.db.query(UserVideo)
            .filter(
                UserVideo.video_id == video_id,
                UserVideo.user_id == user_id,
            )
            .first()
        )

        if user_link:
            self.db.delete(user_link)

        # Clear legacy user_id column if set to this user
        video = (
            self.db.query(Video)
            .filter(Video.video_id == video_id)
            .first()
        )
        if video and video.user_id == user_id:
            video.user_id = None

        self.db.commit()
        return True

    def has_other_references(
        self,
        video_id: str,
        exclude_user_id: int | None = None,
    ) -> bool:
        user_query = self.db.query(UserVideo).filter(
            UserVideo.video_id == video_id
        )
        if exclude_user_id is not None:
            user_query = user_query.filter(
                UserVideo.user_id != exclude_user_id
            )

        if user_query.count() > 0:
            return True

        if exclude_user_id is not None:
            legacy_query = self.db.query(Video).filter(
                Video.video_id == video_id,
                Video.user_id.isnot(None),
                Video.user_id != exclude_user_id,
            )
            if legacy_query.count() > 0:
                return True

        conv_count = (
            self.db.query(Conversation)
            .filter(Conversation.video_id == video_id)
            .count()
        )
        return conv_count > 0

    def update_video_metadata(
        self,
        video_id: str,
        user_id: int,
        title: str | None,
        thumbnail_url: str | None,
    ):
        video = (
            self.db.query(Video)
            .filter(
                Video.video_id == video_id,
            )
            .first()
        )

        if video is None:
            return None

        # Verify user has access
        if not self.get_video(video_id=video_id, user_id=user_id):
            return None

        video.title = title
        video.thumbnail_url = thumbnail_url
        video.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(video)

        return self._to_dict(video)

    def delete_video(
        self,
        video_id: str,
        user_id: int,
    ) -> bool:
        video = self.get_video(
            video_id=video_id,
            user_id=user_id,
        )

        if video is None:
            return False

        other_refs = self.has_other_references(
            video_id=video_id,
            exclude_user_id=user_id,
        )

        self.unlink_user_from_video(
            user_id=user_id,
            video_id=video_id,
        )

        if not other_refs:
            canonical_video = (
                self.db.query(Video)
                .filter(Video.video_id == video_id)
                .first()
            )
            if canonical_video:
                self.db.delete(canonical_video)
                self.db.commit()

        return True

    def get_all_videos(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
        status: str | None = None,
    ):
        query = (
            self.db.query(Video)
            .outerjoin(
                UserVideo,
                UserVideo.video_id == Video.video_id,
            )
            .filter(
                (UserVideo.user_id == user_id) | (Video.user_id == user_id)
            )
            .distinct()
        )

        if status:
            query = query.filter(
                Video.status == status
            )

        videos = (
            query
            .order_by(Video.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [
            self._to_dict(video)
            for video in videos
        ]

    def get_video_count(
        self,
        user_id: int,
        status: str | None = None,
    ) -> int:
        query = (
            self.db.query(
                func.count(func.distinct(Video.id))
            )
            .outerjoin(
                UserVideo,
                UserVideo.video_id == Video.video_id,
            )
            .filter(
                (UserVideo.user_id == user_id) | (Video.user_id == user_id)
            )
        )

        if status:
            query = query.filter(
                Video.status == status
            )

        return query.scalar() or 0

    @staticmethod
    def _to_dict(
        video: Video,
    ):
        return {
            "video_id": video.video_id,
            "title": video.title,
            "thumbnail_url": video.thumbnail_url,
            "status": video.status,
            "segments": video.segments,
            "chunks": video.chunks,
            "created_at": video.created_at,
            "updated_at": video.updated_at,
        }
