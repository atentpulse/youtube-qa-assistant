from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database.database import get_db
from app.models.bug_report import BugReport
from app.models.user import User
from app.schemas.support import BugReportCreate, BugReportResponse

router = APIRouter(
    prefix="/api/support",
    tags=["support"],
)


@router.post(
    "/bug-reports",
    response_model=BugReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an authenticated bug report",
)
def create_bug_report(
    payload: BugReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BugReport:
    """
    Submits a user-reported bug or issue, associating it with the authenticated user.
    Stores the record in PostgreSQL with status 'open'.
    """
    bug_report = BugReport(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        status="open",
    )
    db.add(bug_report)
    db.commit()
    db.refresh(bug_report)
    return bug_report


@router.get(
    "/admin/bug-reports",
    response_model=list[BugReportResponse],
    summary="List all submitted bug reports (admin only)",
)
def list_admin_bug_reports(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[BugReport]:
    """
    Lists all submitted bug reports ordered by creation time.
    Protected strictly by role-based administrator verification.
    """
    reports = (
        db.query(BugReport)
        .order_by(BugReport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return reports
