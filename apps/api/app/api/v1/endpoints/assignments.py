from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core_entities import Assignment, CorrectionResult, Grade, GradeSource
from app.models.domain import AssignmentSubmission, Enrollment, User, UserRole
from app.schemas import (
    AssignmentFeedback,
    AssignmentMasterRead,
    AssignmentRead,
    AssignmentSubmit,
    CorrectionResultRead,
)
from app.services.learning_events import record_learning_event

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("/masters", response_model=list[AssignmentMasterRead])
async def list_assignment_masters(
    course_id: UUID | None = Query(None),
    enrollment_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Assignment]:
    stmt = select(Assignment).order_by(Assignment.sort_order.asc(), Assignment.code.asc())
    if course_id:
        stmt = stmt.where(Assignment.course_id == course_id)
    elif enrollment_id:
        enroll = (
            await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
        ).scalar_one_or_none()
        if enroll is None or (
            enroll.user_id != current_user.id
            and current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.CORRECTOR}
        ):
            raise HTTPException(status_code=404, detail="受講情報が見つかりません")
        stmt = stmt.where(Assignment.course_id == enroll.course_id)
    return list((await db.execute(stmt)).scalars().all())


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

    title = payload.title
    if payload.assignment_id:
        master = (
            await db.execute(select(Assignment).where(Assignment.id == payload.assignment_id))
        ).scalar_one_or_none()
        if master is None or master.course_id != enrollment.course_id:
            raise HTTPException(status_code=400, detail="課題マスタが不正です")
        title = master.title

    submission = AssignmentSubmission(
        enrollment_id=payload.enrollment_id,
        title=title,
        body=payload.body,
    )
    db.add(submission)
    await record_learning_event(
        db,
        enrollment_id=enrollment.id,
        event_type="submit",
        title=f"課題提出: {title}",
        detail=payload.body[:200],
        payload={"assignment_id": str(payload.assignment_id) if payload.assignment_id else None},
    )
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


@router.get("/corrections", response_model=list[CorrectionResultRead])
async def list_corrections(
    enrollment_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CorrectionResult]:
    stmt = select(CorrectionResult).order_by(CorrectionResult.corrected_at.desc())
    if enrollment_id:
        enroll = (
            await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
        ).scalar_one_or_none()
        if enroll is None:
            raise HTTPException(status_code=404, detail="受講情報が見つかりません")
        if enroll.user_id != current_user.id and current_user.role not in {
            UserRole.ADMIN,
            UserRole.INSTRUCTOR,
            UserRole.CORRECTOR,
        }:
            raise HTTPException(status_code=403, detail="権限がありません")
        stmt = stmt.where(CorrectionResult.enrollment_id == enrollment_id)
    elif current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.CORRECTOR}:
        enroll_ids = (
            await db.execute(select(Enrollment.id).where(Enrollment.user_id == current_user.id))
        ).scalars().all()
        stmt = stmt.where(CorrectionResult.enrollment_id.in_(list(enroll_ids) or [None]))
    return list((await db.execute(stmt)).scalars().all())


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
    turnaround = None
    if submission.submitted_at:
        submitted = submission.submitted_at
        if submitted.tzinfo is None:
            submitted = submitted.replace(tzinfo=UTC)
        turnaround = max(0, int((now - submitted).total_seconds() // 3600))
        submission.turnaround_hours = turnaround

    assignment_id = payload.assignment_id
    if assignment_id is None:
        # タイトル一致のマスタを推定
        enroll = (
            await db.execute(select(Enrollment).where(Enrollment.id == submission.enrollment_id))
        ).scalar_one()
        master = (
            await db.execute(
                select(Assignment).where(
                    Assignment.course_id == enroll.course_id,
                    Assignment.title == submission.title,
                )
            )
        ).scalar_one_or_none()
        if master:
            assignment_id = master.id

    score = payload.score if payload.score is not None else 80
    existing_cr = (
        await db.execute(
            select(CorrectionResult).where(CorrectionResult.submission_id == submission.id)
        )
    ).scalar_one_or_none()
    if existing_cr is None:
        db.add(
            CorrectionResult(
                assignment_id=assignment_id,
                submission_id=submission.id,
                enrollment_id=submission.enrollment_id,
                corrector_id=current_user.id,
                score=score,
                status=payload.status,
                feedback=payload.feedback,
                turnaround_hours=turnaround,
                corrected_at=now,
            )
        )
    else:
        existing_cr.assignment_id = assignment_id or existing_cr.assignment_id
        existing_cr.score = score
        existing_cr.status = payload.status
        existing_cr.feedback = payload.feedback
        existing_cr.corrector_id = current_user.id
        existing_cr.turnaround_hours = turnaround
        existing_cr.corrected_at = now

    db.add(
        Grade(
            enrollment_id=submission.enrollment_id,
            source=GradeSource.ASSIGNMENT,
            title=f"添削: {submission.title}",
            score=score,
            max_score=100,
            passed=score >= 60,
        )
    )
    await record_learning_event(
        db,
        enrollment_id=submission.enrollment_id,
        event_type="correction",
        title=f"添削返却: {submission.title}",
        detail=payload.feedback[:200],
        payload={"score": score, "submission_id": str(submission.id)},
    )

    await db.flush()
    await db.refresh(submission)
    return submission
