from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import (
    Application,
    ApplicationStatus,
    Course,
    Enrollment,
    EnrollmentStatus,
    User,
)
from app.schemas import (
    ApplicationCreate,
    ApplicationRead,
    EnrollmentCreate,
    EnrollmentProgressUpdate,
    EnrollmentRead,
)

router = APIRouter(tags=["enrollments"])


@router.get("/enrollments", response_model=list[EnrollmentRead])
async def list_my_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Enrollment]:
    result = await db.execute(
        select(Enrollment).where(Enrollment.user_id == current_user.id).order_by(Enrollment.enrolled_at.desc())
    )
    return list(result.scalars().all())


@router.post("/enrollments", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def enroll(
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Enrollment:
    course = await db.execute(select(Course).where(Course.id == payload.course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")

    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == payload.course_id,
            Enrollment.status.in_(
                [EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE, EnrollmentStatus.RENEWED]
            ),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="既に申込済みです")

    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=payload.course_id,
        status=EnrollmentStatus.ACTIVE,
    )
    db.add(enrollment)

    # 申込転換: 同一ユーザー・コースの APPLIED を CONVERTED に
    apps = await db.execute(
        select(Application).where(
            Application.course_id == payload.course_id,
            Application.email == current_user.email,
            Application.status == ApplicationStatus.APPLIED,
        )
    )
    for app in apps.scalars().all():
        app.status = ApplicationStatus.CONVERTED
        app.converted_at = datetime.now(UTC)
        app.user_id = current_user.id

    await db.flush()
    await db.refresh(enrollment)
    return enrollment


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentRead)
async def get_enrollment(
    enrollment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Enrollment:
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if enrollment is None or enrollment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="受講情報が見つかりません")
    return enrollment


@router.patch("/enrollments/{enrollment_id}/progress", response_model=EnrollmentRead)
async def update_progress(
    enrollment_id: UUID,
    payload: EnrollmentProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Enrollment:
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if enrollment is None or enrollment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="受講情報が見つかりません")

    enrollment.progress_percent = payload.progress_percent
    if payload.status:
        enrollment.status = payload.status
    if payload.progress_percent >= 100 or payload.status == EnrollmentStatus.COMPLETED:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(enrollment)
    return enrollment


@router.post("/enrollments/{enrollment_id}/renew", response_model=EnrollmentRead)
async def renew_enrollment(
    enrollment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Enrollment:
    """継続率向上: 受講継続（更新）."""
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if enrollment is None or enrollment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="受講情報が見つかりません")
    enrollment.status = EnrollmentStatus.RENEWED
    enrollment.renewed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(enrollment)
    return enrollment


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
) -> Application:
    """未ログインでも申込可能（転換率ファネルの入口）."""
    course = await db.execute(select(Course).where(Course.id == payload.course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")

    app = Application(**payload.model_dump(), status=ApplicationStatus.APPLIED)
    db.add(app)
    await db.flush()
    await db.refresh(app)
    return app


@router.get("/applications", response_model=list[ApplicationRead])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Application]:
    if current_user.role.value not in {"ADMIN", "INSTRUCTOR", "CORPORATE_MANAGER"}:
        result = await db.execute(
            select(Application).where(Application.email == current_user.email).order_by(Application.created_at.desc())
        )
    else:
        result = await db.execute(select(Application).order_by(Application.created_at.desc()))
    return list(result.scalars().all())
