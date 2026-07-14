"""学習管理 API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import Enrollment, User, UserRole
from app.models.platform import (
    Bookmark,
    ComprehensionQuiz,
    ContentPrerequisite,
    LearningContent,
    LearningProgress,
    LearningReminder,
    QuizAttempt,
)
from app.schemas.platform import (
    BookmarkCreate,
    BookmarkRead,
    LearningContentCreate,
    LearningContentRead,
    ProgressRead,
    ProgressUpdate,
    QuizAttemptRead,
    QuizCreate,
    QuizRead,
    QuizSubmit,
    ReminderCreate,
    ReminderRead,
)

router = APIRouter(tags=["learning"])


@router.post("/learning/contents", response_model=LearningContentRead, status_code=201)
async def create_content(
    payload: LearningContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningContent:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="教材登録権限がありません")
    data = payload.model_dump(exclude={"prerequisite_content_ids"})
    content = LearningContent(**data)
    db.add(content)
    await db.flush()
    for pre_id in payload.prerequisite_content_ids:
        db.add(ContentPrerequisite(content_id=content.id, prerequisite_content_id=pre_id))
    await db.flush()
    await db.refresh(content)
    return content


@router.get("/learning/contents", response_model=list[LearningContentRead])
async def list_contents(
    course_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[LearningContent]:
    stmt = select(LearningContent).order_by(LearningContent.sort_order.asc())
    if course_id:
        stmt = stmt.where(LearningContent.course_id == course_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/learning/contents/{content_id}/prerequisites", response_model=list[LearningContentRead])
async def list_prerequisites(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[LearningContent]:
    pre_ids = (
        await db.execute(
            select(ContentPrerequisite.prerequisite_content_id).where(
                ContentPrerequisite.content_id == content_id
            )
        )
    ).scalars().all()
    if not pre_ids:
        return []
    result = await db.execute(select(LearningContent).where(LearningContent.id.in_(pre_ids)))
    return list(result.scalars().all())


@router.post("/learning/progress", response_model=ProgressRead)
async def upsert_progress(
    payload: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningProgress:
    enroll = (await db.execute(select(Enrollment).where(Enrollment.id == payload.enrollment_id))).scalar_one_or_none()
    if enroll is None or enroll.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="受講情報が見つかりません")

    # 前提科目チェック
    pre_ids = (
        await db.execute(
            select(ContentPrerequisite.prerequisite_content_id).where(
                ContentPrerequisite.content_id == payload.content_id
            )
        )
    ).scalars().all()
    for pre_id in pre_ids:
        pre_prog = (
            await db.execute(
                select(LearningProgress).where(
                    LearningProgress.enrollment_id == payload.enrollment_id,
                    LearningProgress.content_id == pre_id,
                    LearningProgress.completed.is_(True),
                )
            )
        ).scalar_one_or_none()
        if pre_prog is None:
            raise HTTPException(status_code=400, detail="前提科目が未完了です")

    existing = (
        await db.execute(
            select(LearningProgress).where(
                LearningProgress.enrollment_id == payload.enrollment_id,
                LearningProgress.content_id == payload.content_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = LearningProgress(
            enrollment_id=payload.enrollment_id,
            content_id=payload.content_id,
        )
        db.add(existing)
    existing.progress_percent = payload.progress_percent
    existing.completed = payload.progress_percent >= 100
    existing.last_accessed_at = datetime.now(UTC)
    if payload.deadline_at:
        existing.deadline_at = payload.deadline_at

    # 受講全体の進捗率を更新
    contents = (
        await db.execute(select(func.count()).select_from(LearningContent).where(LearningContent.course_id == enroll.course_id))
    ).scalar_one()
    if contents:
        done = (
            await db.execute(
                select(func.count())
                .select_from(LearningProgress)
                .where(LearningProgress.enrollment_id == enroll.id, LearningProgress.completed.is_(True))
            )
        ).scalar_one()
        enroll.progress_percent = int(round(100 * done / contents))

    await db.flush()
    await db.refresh(existing)
    return existing


@router.get("/learning/progress", response_model=list[ProgressRead])
async def list_progress(
    enrollment_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LearningProgress]:
    enroll = (await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))).scalar_one_or_none()
    if enroll is None or enroll.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="受講情報が見つかりません")
    result = await db.execute(select(LearningProgress).where(LearningProgress.enrollment_id == enrollment_id))
    return list(result.scalars().all())


@router.post("/learning/bookmarks", response_model=BookmarkRead, status_code=201)
async def add_bookmark(
    payload: BookmarkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Bookmark:
    bm = Bookmark(user_id=current_user.id, content_id=payload.content_id, note=payload.note)
    db.add(bm)
    await db.flush()
    await db.refresh(bm)
    return bm


@router.get("/learning/bookmarks", response_model=list[BookmarkRead])
async def list_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Bookmark]:
    result = await db.execute(select(Bookmark).where(Bookmark.user_id == current_user.id))
    return list(result.scalars().all())


@router.post("/learning/quizzes", response_model=QuizRead, status_code=201)
async def create_quiz(
    payload: QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComprehensionQuiz:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="クイズ作成権限がありません")
    quiz = ComprehensionQuiz(**payload.model_dump())
    db.add(quiz)
    await db.flush()
    await db.refresh(quiz)
    return quiz


@router.get("/learning/quizzes", response_model=list[QuizRead])
async def list_quizzes(
    content_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ComprehensionQuiz]:
    stmt = select(ComprehensionQuiz)
    if content_id:
        stmt = stmt.where(ComprehensionQuiz.content_id == content_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/learning/quizzes/{quiz_id}/submit", response_model=QuizAttemptRead)
async def submit_quiz(
    quiz_id: str,
    payload: QuizSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizAttempt:
    quiz = (await db.execute(select(ComprehensionQuiz).where(ComprehensionQuiz.id == quiz_id))).scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=404, detail="クイズが見つかりません")
    attempt_count = (
        await db.execute(
            select(func.count())
            .select_from(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == current_user.id)
        )
    ).scalar_one()
    if attempt_count >= quiz.max_attempts:
        raise HTTPException(status_code=400, detail="再受験回数の上限に達しています")

    questions = quiz.questions or []
    correct = 0
    total = max(len(questions), 1)
    for q in questions:
        if payload.answers.get(str(q.get("id", ""))) == q.get("answer"):
            correct += 1
    score = int(round(100 * correct / total))
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        score=score,
        passed=score >= quiz.passing_score,
        answers=payload.answers,
        attempt_no=attempt_count + 1,
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)
    return attempt


@router.post("/learning/reminders", response_model=ReminderRead, status_code=201)
async def send_reminder(
    payload: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningReminder:
    """未受講者への督促."""
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.CORPORATE_MANAGER}:
        raise HTTPException(status_code=403, detail="督促送信権限がありません")
    enroll = (await db.execute(select(Enrollment).where(Enrollment.id == payload.enrollment_id))).scalar_one_or_none()
    if enroll is None:
        raise HTTPException(status_code=404, detail="受講情報が見つかりません")
    rem = LearningReminder(
        enrollment_id=enroll.id,
        message=payload.message,
        channel=payload.channel,
    )
    db.add(rem)
    await db.flush()
    await db.refresh(rem)
    return rem


@router.get("/learning/reminders", response_model=list[ReminderRead])
async def list_reminders(
    enrollment_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[LearningReminder]:
    stmt = select(LearningReminder).order_by(LearningReminder.sent_at.desc())
    if enrollment_id:
        stmt = stmt.where(LearningReminder.enrollment_id == enrollment_id)
    return list((await db.execute(stmt)).scalars().all())
