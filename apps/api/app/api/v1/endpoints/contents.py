from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import Course, Material, MediaContent, User, UserRole
from app.schemas import MaterialCreate, MaterialRead, MediaCreate, MediaRead

router = APIRouter(tags=["contents"])


def _require_ops(user: User) -> None:
    if user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="コンテンツ管理権限がありません")


@router.get("/materials", response_model=list[MaterialRead])
async def list_materials(
    course_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Material]:
    stmt = select(Material).order_by(Material.created_at.desc())
    if course_id:
        stmt = stmt.where(Material.course_id == course_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
async def create_material(
    payload: MaterialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Material:
    _require_ops(current_user)
    course = await db.execute(select(Course).where(Course.id == payload.course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")
    material = Material(**payload.model_dump())
    db.add(material)
    await db.flush()
    await db.refresh(material)
    return material


@router.get("/media", response_model=list[MediaRead])
async def list_media(
    course_id: UUID | None = Query(None),
    live_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MediaContent]:
    stmt = select(MediaContent).order_by(MediaContent.created_at.desc())
    if course_id:
        stmt = stmt.where(MediaContent.course_id == course_id)
    if live_only:
        stmt = stmt.where(MediaContent.is_live_now.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/media", response_model=MediaRead, status_code=status.HTTP_201_CREATED)
async def create_media(
    payload: MediaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MediaContent:
    _require_ops(current_user)
    course = await db.execute(select(Course).where(Course.id == payload.course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コースが見つかりません")
    media = MediaContent(**payload.model_dump())
    db.add(media)
    await db.flush()
    await db.refresh(media)
    return media
