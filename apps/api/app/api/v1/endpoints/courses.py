from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import Course, CourseStatus, Lesson, ServiceType, User, UserRole
from app.schemas import CourseCreate, CourseRead, CourseUpdate, LessonCreate, LessonRead

router = APIRouter(prefix="/courses", tags=["courses"])


def _require_ops(user: User) -> None:
    if user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="商品管理権限がありません")


@router.get("", response_model=list[CourseRead])
async def list_courses(
    service_type: ServiceType | None = Query(None),
    audience: str | None = Query(None),
    status_filter: CourseStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Course]:
    stmt = select(Course).order_by(Course.created_at.desc())
    if status_filter:
        stmt = stmt.where(Course.status == status_filter)
    result = await db.execute(stmt)
    courses = list(result.scalars().all())
    if service_type:
        courses = [c for c in courses if service_type.value in (c.service_types or [])]
    if audience:
        courses = [c for c in courses if c.audience.value == audience or c.audience.value == "both"]
    return courses


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    _require_ops(current_user)
    exists = await db.execute(select(Course).where(Course.code == payload.code))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="コースコードが重複しています")

    data = payload.model_dump()
    data["service_types"] = [s.value if hasattr(s, "value") else s for s in data.get("service_types", [])]
    course = Course(**data, draft_started_at=datetime.now(UTC))
    if course.status == CourseStatus.PUBLISHED:
        course.published_at = datetime.now(UTC)
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Course:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")
    return course


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    _require_ops(current_user)
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")

    data = payload.model_dump(exclude_unset=True)
    if "service_types" in data and data["service_types"] is not None:
        data["service_types"] = [s.value if hasattr(s, "value") else s for s in data["service_types"]]
    prev_status = course.status
    for key, value in data.items():
        setattr(course, key, value)
    if course.status == CourseStatus.PUBLISHED and prev_status != CourseStatus.PUBLISHED:
        course.published_at = datetime.now(UTC)
        if course.draft_started_at is None:
            course.draft_started_at = course.created_at
    await db.flush()
    await db.refresh(course)
    return course


@router.get("/{course_id}/lessons", response_model=list[LessonRead])
async def list_lessons(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Lesson]:
    result = await db.execute(
        select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.sort_order.asc())
    )
    return list(result.scalars().all())


@router.post("/{course_id}/lessons", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    course_id: UUID,
    payload: LessonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Lesson:
    _require_ops(current_user)
    course = await db.execute(select(Course).where(Course.id == course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")
    lesson = Lesson(course_id=course_id, **payload.model_dump())
    db.add(lesson)
    await db.flush()
    await db.refresh(lesson)
    return lesson
