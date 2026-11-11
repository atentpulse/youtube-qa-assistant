from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User

from app.schemas.video import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    VideoListResponse,
    VideoStatusResponse,
)

from app.services.rag_service import RAGService
from app.services.video_storage_service import VideoStorageService

from app.dependencies import get_rag_service
from app.core.rate_limiter import check_video_process_rate_limit


router = APIRouter(
    tags=["Videos"],
)


# --------------------------------
# Process video
# --------------------------------

@router.post(
    "/videos/process",
    response_model=ProcessVideoResponse,
    dependencies=[Depends(check_video_process_rate_limit)],
)
def process_video(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
):

    try:

        result = rag_service.process_video(
            db=db,
            user_id=current_user.id,
            url=request.url.strip(),
            force_reprocess=request.force_reprocess,
        )

        # Start background processing
        if result["status"] == "processing":

            background_tasks.add_task(
                rag_service.process_video_background,
                result["video_id"],
                current_user.id,
            )

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred "
                "while processing the video."
            ),
        )


# --------------------------------
# Get all videos
# --------------------------------

@router.get(
    "/videos",
    response_model=VideoListResponse,
)
def get_all_videos(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    status: str | None = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
):

    if status:

        status = status.strip().lower()

    return rag_service.get_all_videos(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status,
    )


# --------------------------------
# Get video status
# --------------------------------

@router.get(
    "/videos/{video_id}/status",
    response_model=VideoStatusResponse,
)
def get_video_status(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    video_id = video_id.strip()

    video_storage = VideoStorageService(db)

    video = video_storage.get_video(
        video_id=video_id,
        user_id=current_user.id,
    )

    if video is None:

        raise HTTPException(
            status_code=404,
            detail="Video not found.",
        )

    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "thumbnail_url": video["thumbnail_url"],
        "status": video["status"],
        "segments": video["segments"],
        "chunks": video["chunks"],
        "error_message": video.get("error_message"),
        "processing_started_at": video.get("processing_started_at"),
    }


# --------------------------------
# Delete video
# --------------------------------

@router.delete(
    "/videos/{video_id}",
)
def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
):

    try:

        result = rag_service.delete_video(
            db=db,
            user_id=current_user.id,
            video_id=video_id.strip(),
        )

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )