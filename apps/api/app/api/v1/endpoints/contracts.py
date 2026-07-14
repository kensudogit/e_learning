"""申込・契約 API."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import Course, Enrollment, EnrollmentStatus, Material, User, UserRole
from app.models.platform import (
    BillingDocument,
    Contract,
    ContractChange,
    ContractItem,
    ContractStatus,
    Coupon,
    DocumentType,
    InstallmentSchedule,
    PaymentMethod,
    ShippingAddress,
    ShippingOrder,
    ShippingStatus,
)
from app.schemas.platform import (
    ContractChangeCreate,
    ContractCreate,
    ContractItemRead,
    ContractRead,
    CouponCreate,
    CouponRead,
    DocumentIssue,
    DocumentRead,
    InstallmentRead,
)

router = APIRouter(prefix="/contracts", tags=["contracts"])


def _contract_no() -> str:
    return f"CT-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"


def _doc_no(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"


@router.post("/coupons", response_model=CouponRead, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    payload: CouponCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Coupon:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="クーポン作成権限がありません")
    exists = await db.execute(select(Coupon).where(Coupon.code == payload.code))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="クーポンコードが重複しています")
    coupon = Coupon(**payload.model_dump())
    db.add(coupon)
    await db.flush()
    await db.refresh(coupon)
    return coupon


@router.get("/coupons", response_model=list[CouponRead])
async def list_coupons(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[Coupon]:
    result = await db.execute(select(Coupon).where(Coupon.is_active.is_(True)).order_by(Coupon.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Contract:
    """個人/法人申込・複数講座同時・クーポン/紹介/キャンペーン・分割払い."""
    discount = Decimal("0")
    coupon_id = None
    if payload.coupon_code:
        c = (await db.execute(select(Coupon).where(Coupon.code == payload.coupon_code, Coupon.is_active.is_(True)))).scalar_one_or_none()
        if c is None:
            raise HTTPException(status_code=400, detail="無効なクーポンです")
        coupon_id = c.id
        # 割引は後で合計から計算

    total = Decimal("0")
    for item in payload.items:
        course = (await db.execute(select(Course).where(Course.id == item.course_id))).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=404, detail=f"コースが見つかりません: {item.course_id}")
        price = item.unit_price if item.unit_price else (course.price or Decimal("0"))
        total += Decimal(price)

    if coupon_id:
        c = (await db.execute(select(Coupon).where(Coupon.id == coupon_id))).scalar_one()
        if c.discount_percent:
            discount = (total * Decimal(c.discount_percent) / Decimal(100)).quantize(Decimal("1"))
        elif c.discount_amount:
            discount = Decimal(c.discount_amount)
        discount = min(discount, total)

    contract = Contract(
        contract_no=_contract_no(),
        contract_type=payload.contract_type,
        channel=payload.channel,
        status=ContractStatus.ACTIVE,
        contractor_user_id=current_user.id,
        organization_id=payload.organization_id,
        agency_name=payload.agency_name,
        coupon_id=coupon_id,
        referral_code=payload.referral_code,
        campaign_name=payload.campaign_name,
        start_date=payload.start_date or date.today(),
        end_date=payload.end_date,
        payment_method=payload.payment_method,
        installment_count=payload.installment_count,
        total_amount=total - discount,
        discount_amount=discount,
        notes=payload.notes,
    )
    current_user.is_contractor = True
    db.add(contract)
    await db.flush()

    for item in payload.items:
        course = (await db.execute(select(Course).where(Course.id == item.course_id))).scalar_one()
        unit = item.unit_price if item.unit_price else (course.price or Decimal("0"))
        learner_id = item.learner_user_id or current_user.id
        enrollment = Enrollment(
            user_id=learner_id,
            course_id=item.course_id,
            status=EnrollmentStatus.ACTIVE,
            progress_percent=0,
        )
        db.add(enrollment)
        await db.flush()
        db.add(
            ContractItem(
                contract_id=contract.id,
                course_id=item.course_id,
                learner_user_id=learner_id,
                enrollment_id=enrollment.id,
                unit_price=unit,
                start_date=item.start_date or contract.start_date,
                end_date=item.end_date or contract.end_date,
            )
        )

        # 紙教材（shipping_required）があれば分割発送予定を自動作成
        materials = (
            await db.execute(
                select(Material).where(
                    Material.course_id == item.course_id,
                    Material.shipping_required.is_(True),
                )
            )
        ).scalars().all()
        if materials:
            addr = (
                await db.execute(
                    select(ShippingAddress)
                    .where(ShippingAddress.user_id == learner_id)
                    .order_by(ShippingAddress.is_default.desc(), ShippingAddress.created_at.asc())
                )
            ).scalars().first()
            if addr is None:
                addr = ShippingAddress(
                    user_id=learner_id,
                    label="契約時自動登録",
                    postal_code="100-0001",
                    country="JP",
                    prefecture="東京都",
                    city="千代田区",
                    address_line="1-1（契約時仮住所・変更可）",
                    is_default=True,
                )
                db.add(addr)
                await db.flush()
            split_group = f"AUTO-{contract.contract_no}-{str(enrollment.id)[:8]}"
            for seq, mat in enumerate(materials, start=1):
                db.add(
                    ShippingOrder(
                        enrollment_id=enrollment.id,
                        contract_id=contract.id,
                        address_id=addr.id,
                        material_id=mat.id,
                        status=ShippingStatus.SCHEDULED,
                        scheduled_ship_date=(contract.start_date or date.today())
                        + timedelta(days=2 + (seq - 1) * 14),
                        split_group=split_group,
                        split_sequence=seq,
                        is_overseas=addr.country != "JP",
                    )
                )

    # 分割払いスケジュール
    if payload.payment_method == PaymentMethod.INSTALLMENT and payload.installment_count:
        n = payload.installment_count
        each = (contract.total_amount / n).quantize(Decimal("1"))
        remainder = contract.total_amount - each * (n - 1)
        for i in range(1, n + 1):
            db.add(
                InstallmentSchedule(
                    contract_id=contract.id,
                    installment_no=i,
                    due_date=(contract.start_date or date.today()) + timedelta(days=30 * i),
                    amount=remainder if i == n else each,
                )
            )

    await db.flush()
    await db.refresh(contract)
    return contract


@router.get("", response_model=list[ContractRead])
async def list_contracts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Contract]:
    if current_user.role in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        result = await db.execute(select(Contract).order_by(Contract.created_at.desc()))
    else:
        result = await db.execute(
            select(Contract)
            .where(Contract.contractor_user_id == current_user.id)
            .order_by(Contract.created_at.desc())
        )
    return list(result.scalars().all())


@router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Contract:
    contract = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="契約が見つかりません")
    return contract


@router.get("/{contract_id}/items", response_model=list[ContractItemRead])
async def list_items(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ContractItem]:
    result = await db.execute(select(ContractItem).where(ContractItem.contract_id == contract_id))
    return list(result.scalars().all())


@router.post("/{contract_id}/changes", response_model=ContractRead)
async def change_contract(
    contract_id: str,
    payload: ContractChangeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Contract:
    contract = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="契約が見つかりません")
    db.add(
        ContractChange(
            contract_id=contract.id,
            change_type=payload.change_type,
            reason=payload.reason,
            requested_by=current_user.id,
            effective_date=payload.effective_date or date.today(),
        )
    )
    if payload.change_type == "cancel":
        contract.status = ContractStatus.CANCELLED
    elif payload.change_type == "terminate":
        contract.status = ContractStatus.TERMINATED
    else:
        contract.status = ContractStatus.CHANGED
    await db.flush()
    await db.refresh(contract)
    return contract


@router.get("/{contract_id}/installments", response_model=list[InstallmentRead])
async def list_installments(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[InstallmentSchedule]:
    result = await db.execute(
        select(InstallmentSchedule)
        .where(InstallmentSchedule.contract_id == contract_id)
        .order_by(InstallmentSchedule.installment_no.asc())
    )
    return list(result.scalars().all())


@router.post("/{contract_id}/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def issue_document(
    contract_id: str,
    payload: DocumentIssue,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillingDocument:
    """見積・請求書・領収書の発行."""
    contract = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="契約が見つかりません")
    prefix = {DocumentType.QUOTE: "QT", DocumentType.INVOICE: "INV", DocumentType.RECEIPT: "RC"}.get(
        payload.doc_type, "DOC"
    )
    if payload.doc_type == DocumentType.QUOTE:
        contract.status = ContractStatus.QUOTED
    doc = BillingDocument(
        contract_id=contract.id,
        doc_type=payload.doc_type,
        document_no=_doc_no(prefix),
        amount=contract.total_amount,
        payload={
            "contract_no": contract.contract_no,
            "issued_by": str(current_user.id),
            "channel": contract.channel.value,
        },
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.get("/{contract_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[BillingDocument]:
    result = await db.execute(
        select(BillingDocument)
        .where(BillingDocument.contract_id == contract_id)
        .order_by(BillingDocument.issued_at.desc())
    )
    return list(result.scalars().all())
