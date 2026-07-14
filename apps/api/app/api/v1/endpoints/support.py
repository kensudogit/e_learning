from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import FaqArticle, Inquiry, InquiryStatus, User, UserRole
from app.schemas import FaqCreate, FaqRead, InquiryAnswer, InquiryCreate, InquiryRead

router = APIRouter(tags=["support"])


@router.get("/faqs", response_model=list[FaqRead])
async def list_faqs(
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[FaqArticle]:
    stmt = select(FaqArticle).where(FaqArticle.is_published.is_(True)).order_by(FaqArticle.view_count.desc())
    if category:
        stmt = stmt.where(FaqArticle.category == category)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/faqs", response_model=FaqRead, status_code=status.HTTP_201_CREATED)
async def create_faq(
    payload: FaqCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaqArticle:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FAQ 管理権限がありません")
    faq = FaqArticle(**payload.model_dump())
    db.add(faq)
    await db.flush()
    await db.refresh(faq)
    return faq


@router.post("/faqs/{faq_id}/view", response_model=FaqRead)
async def view_faq(faq_id: UUID, db: AsyncSession = Depends(get_db)) -> FaqArticle:
    result = await db.execute(select(FaqArticle).where(FaqArticle.id == faq_id))
    faq = result.scalar_one_or_none()
    if faq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQが見つかりません")
    faq.view_count += 1
    await db.flush()
    await db.refresh(faq)
    return faq


@router.post("/faqs/{faq_id}/helpful", response_model=FaqRead)
async def mark_helpful(faq_id: UUID, db: AsyncSession = Depends(get_db)) -> FaqArticle:
    result = await db.execute(select(FaqArticle).where(FaqArticle.id == faq_id))
    faq = result.scalar_one_or_none()
    if faq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQが見つかりません")
    faq.helpful_count += 1
    await db.flush()
    await db.refresh(faq)
    return faq


@router.post("/inquiries", response_model=InquiryRead, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    payload: InquiryCreate,
    db: AsyncSession = Depends(get_db),
) -> Inquiry:
    # FAQ に同一カテゴリがあれば自己解決候補としてフラグ
    faq = await db.execute(
        select(FaqArticle).where(FaqArticle.category == payload.category, FaqArticle.is_published.is_(True)).limit(1)
    )
    has_faq = faq.scalar_one_or_none() is not None
    inquiry = Inquiry(**payload.model_dump(), resolved_by_faq=False)
    if has_faq:
        inquiry.answer = "関連 FAQ をご確認ください。解決した場合は追加のお問い合わせは不要です。"
    db.add(inquiry)
    await db.flush()
    await db.refresh(inquiry)
    return inquiry


@router.post("/inquiries/{inquiry_id}/resolve-faq", response_model=InquiryRead)
async def resolve_by_faq(
    inquiry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Inquiry:
    result = await db.execute(select(Inquiry).where(Inquiry.id == inquiry_id))
    inquiry = result.scalar_one_or_none()
    if inquiry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問い合わせが見つかりません")
    inquiry.resolved_by_faq = True
    inquiry.status = InquiryStatus.CLOSED
    inquiry.answered_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(inquiry)
    return inquiry


@router.get("/inquiries", response_model=list[InquiryRead])
async def list_inquiries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Inquiry]:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        result = await db.execute(
            select(Inquiry).where(Inquiry.email == current_user.email).order_by(Inquiry.created_at.desc())
        )
    else:
        result = await db.execute(select(Inquiry).order_by(Inquiry.created_at.desc()))
    return list(result.scalars().all())


@router.post("/inquiries/{inquiry_id}/answer", response_model=InquiryRead)
async def answer_inquiry(
    inquiry_id: UUID,
    payload: InquiryAnswer,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Inquiry:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="回答権限がありません")
    result = await db.execute(select(Inquiry).where(Inquiry.id == inquiry_id))
    inquiry = result.scalar_one_or_none()
    if inquiry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="問い合わせが見つかりません")
    inquiry.answer = payload.answer
    inquiry.status = payload.status
    inquiry.answered_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(inquiry)
    return inquiry
