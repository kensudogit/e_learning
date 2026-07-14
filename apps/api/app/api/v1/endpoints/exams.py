from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import (
    AttemptStatus,
    Certificate,
    Course,
    Enrollment,
    EnrollmentStatus,
    Exam,
    ExamAttempt,
    User,
    UserRole,
)
from app.schemas import (
    CertificateIssue,
    CertificateRead,
    ExamAttemptRead,
    ExamCreate,
    ExamRead,
    ExamSubmit,
)

router = APIRouter(tags=["exams"])


@router.get("/exams", response_model=list[ExamRead])
async def list_exams(
    course_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Exam]:
    stmt = select(Exam).order_by(Exam.created_at.desc())
    if course_id:
        stmt = stmt.where(Exam.course_id == course_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/exams", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Exam:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="試験作成権限がありません")
    course = await db.execute(select(Course).where(Course.id == payload.course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")
    exam = Exam(**payload.model_dump())
    db.add(exam)
    await db.flush()
    await db.refresh(exam)
    return exam


@router.post("/exams/{exam_id}/submit", response_model=ExamAttemptRead)
async def submit_exam(
    exam_id: UUID,
    payload: ExamSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamAttempt:
    exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="試験が見つかりません")

    enroll_result = await db.execute(select(Enrollment).where(Enrollment.id == payload.enrollment_id))
    enrollment = enroll_result.scalar_one_or_none()
    if enrollment is None or enrollment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="受講情報が見つかりません")
    if enrollment.course_id != exam.course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="コースが一致しません")

    questions = exam.questions or []
    correct = 0
    total = max(len(questions), 1)
    for q in questions:
        qid = str(q.get("id", ""))
        if payload.answers.get(qid) == q.get("answer"):
            correct += 1
    score = int(round(100 * correct / total))
    passed = score >= exam.passing_score

    attempt = ExamAttempt(
        exam_id=exam.id,
        enrollment_id=enrollment.id,
        score=score,
        status=AttemptStatus.PASSED if passed else AttemptStatus.FAILED,
        answers=payload.answers,
        submitted_at=datetime.now(UTC),
    )
    db.add(attempt)

    if passed:
        enrollment.progress_percent = max(enrollment.progress_percent, 100)
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = datetime.now(UTC)
        cert = Certificate(
            enrollment_id=enrollment.id,
            certificate_no=f"CERT-{uuid4().hex[:10].upper()}",
            title=f"{exam.title} 修了認定",
        )
        db.add(cert)

    await db.flush()
    await db.refresh(attempt)
    return attempt


@router.post("/certificates/issue", response_model=CertificateRead, status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    payload: CertificateIssue,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Certificate:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="認定発行権限がありません")
    enroll_result = await db.execute(select(Enrollment).where(Enrollment.id == payload.enrollment_id))
    enrollment = enroll_result.scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="受講情報が見つかりません")

    course = (await db.execute(select(Course).where(Course.id == enrollment.course_id))).scalar_one()
    cert = Certificate(
        enrollment_id=enrollment.id,
        certificate_no=f"CERT-{uuid4().hex[:10].upper()}",
        title=payload.title or f"{course.title} 修了認定",
    )
    db.add(cert)
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.completed_at = datetime.now(UTC)
    enrollment.progress_percent = 100
    await db.flush()
    await db.refresh(cert)
    return cert


@router.get("/certificates/mine", response_model=list[CertificateRead])
async def my_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Certificate]:
    enroll_ids = (
        await db.execute(select(Enrollment.id).where(Enrollment.user_id == current_user.id))
    ).scalars().all()
    result = await db.execute(
        select(Certificate)
        .where(Certificate.enrollment_id.in_(list(enroll_ids) or [None]))
        .order_by(Certificate.issued_at.desc())
    )
    return list(result.scalars().all())
