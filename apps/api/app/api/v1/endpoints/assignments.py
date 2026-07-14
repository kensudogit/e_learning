from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import AssignmentSubmission, Enrollment, User, UserRole
from app.schemas import AssignmentFeedback, AssignmentRead, AssignmentSubmit

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("/submit", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    payload: AssignmentSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssignmentSubmission:
    result = await db.execute(select(Enrollment).where(Enrollment.id == payload.enrollment_id))
    enrollment = result.scalar_one_or_none()
    if enrollment is None or enrollment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="受講情報が見つかりません")

    submission = AssignmentSubmission(
        enrollment_id=payload.enrollment_id,
        title=payload.title,
        body=payload.body,
    )
    db.add(submission)
    await db.flush()
    await db.refresh(submission)
    return submission


@router.get("/mine", response_model=list[AssignmentRead])
async def list_my_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentSubmission]:
    enroll_ids = (
        await db.execute(select(Enrollment.id).where(Enrollment.user_id == current_user.id))
    ).scalars().all()
    result = await db.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.enrollment_id.in_(list(enroll_ids) or [None]))
        .order_by(AssignmentSubmission.submitted_at.desc())
    )
    return list(result.scalars().all())


@router.get("/pending", response_model=list[AssignmentRead])
async def list_pending_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentSubmission]:
    if current_user.role not in {UserRole.CORRECTOR, UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="添削権限がありません")

    result = await db.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.status.in_(["submitted", "reviewing"]))
        .order_by(AssignmentSubmission.submitted_at.asc())
    )
    return list(result.scalars().all())


@router.post("/{submission_id}/feedback", response_model=AssignmentRead)
async def give_feedback(
    submission_id: UUID,
    payload: AssignmentFeedback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssignmentSubmission:
    if current_user.role not in {UserRole.CORRECTOR, UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="添削権限がありません")

    result = await db.execute(select(AssignmentSubmission).where(AssignmentSubmission.id == submission_id))
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提出物が見つかりません")

    now = datetime.now(UTC)
    submission.feedback = payload.feedback
    submission.status = payload.status
    submission.reviewed_at = now
    submission.corrector_id = current_user.id
    if submission.submitted_at:
        submitted = submission.submitted_at
        if submitted.tzinfo is None:
            submitted = submitted.replace(tzinfo=UTC)
        submission.turnaround_hours = max(0, int((now - submitted).total_seconds() // 3600))
    await db.flush()
    await db.refresh(submission)
    return submission
