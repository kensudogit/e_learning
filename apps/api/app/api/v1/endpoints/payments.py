"""入金 API（通信教育の請求・分割払いと連動）."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core_entities import Payment, PaymentStatus
from app.models.domain import User, UserRole
from app.models.platform import Contract, InstallmentSchedule
from app.schemas import ORMModel

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentCreate(BaseModel):
    contract_id: UUID
    amount: Decimal = Field(gt=0)
    method: str = "bank_transfer"
    status: PaymentStatus = PaymentStatus.RECEIVED
    note: str | None = None
    installment_no: int | None = Field(default=None, ge=1)
    billing_document_id: UUID | None = None


class PaymentRead(ORMModel):
    id: UUID
    payment_no: str
    contract_id: UUID | None
    amount: Decimal
    method: str
    status: PaymentStatus
    paid_at: datetime | None
    note: str | None
    created_at: datetime


def _payment_no() -> str:
    return f"PAY-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"


@router.get("", response_model=list[PaymentRead])
async def list_payments(
    contract_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.created_at.desc())
    if contract_id:
        stmt = stmt.where(Payment.contract_id == contract_id)
    elif current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        contract_ids = (
            await db.execute(
                select(Contract.id).where(Contract.contractor_user_id == current_user.id)
            )
        ).scalars().all()
        stmt = stmt.where(Payment.contract_id.in_(list(contract_ids) or [None]))
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    contract = (
        await db.execute(select(Contract).where(Contract.id == payload.contract_id))
    ).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="契約が見つかりません")
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        if contract.contractor_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="入金登録権限がありません")

    paid_at = datetime.now(UTC) if payload.status == PaymentStatus.RECEIVED else None
    payment = Payment(
        payment_no=_payment_no(),
        contract_id=contract.id,
        billing_document_id=payload.billing_document_id,
        amount=payload.amount,
        method=payload.method,
        status=payload.status,
        paid_at=paid_at,
        note=payload.note,
    )
    db.add(payment)

    if payload.installment_no is not None and payload.status == PaymentStatus.RECEIVED:
        inst = (
            await db.execute(
                select(InstallmentSchedule).where(
                    InstallmentSchedule.contract_id == contract.id,
                    InstallmentSchedule.installment_no == payload.installment_no,
                )
            )
        ).scalar_one_or_none()
        if inst is None:
            raise HTTPException(status_code=404, detail="分割回次が見つかりません")
        inst.paid = True
        inst.paid_at = paid_at

    await db.flush()
    await db.refresh(payment)
    return payment


@router.post("/installments/{installment_id}/pay", response_model=PaymentRead, status_code=201)
async def pay_installment(
    installment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    """分割回次を入金済みにし、Payment レコードを作成."""
    inst = (
        await db.execute(select(InstallmentSchedule).where(InstallmentSchedule.id == installment_id))
    ).scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=404, detail="分割スケジュールが見つかりません")
    contract = (
        await db.execute(select(Contract).where(Contract.id == inst.contract_id))
    ).scalar_one()
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        if contract.contractor_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="入金登録権限がありません")
    if inst.paid:
        raise HTTPException(status_code=400, detail="既に入金済みです")

    now = datetime.now(UTC)
    inst.paid = True
    inst.paid_at = now
    payment = Payment(
        payment_no=_payment_no(),
        contract_id=contract.id,
        amount=inst.amount,
        method=contract.payment_method.value if contract.payment_method else "installment",
        status=PaymentStatus.RECEIVED,
        paid_at=now,
        note=f"分割第{inst.installment_no}回",
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment
