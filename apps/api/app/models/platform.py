"""申込・契約 / アカウント / 学習管理 / 教材発送 の拡張ドメイン."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.domain import _enum


# --- Enums ---
class ContractType(str, enum.Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"


class IntakeChannel(str, enum.Enum):
    WEB = "web"
    PHONE = "phone"
    MAIL = "mail"
    AGENCY = "agency"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    ACTIVE = "active"
    CHANGED = "changed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"
    COMPLETED = "completed"


class PaymentMethod(str, enum.Enum):
    LUMP_SUM = "lump_sum"
    INSTALLMENT = "installment"
    INVOICE = "invoice"


class DocumentType(str, enum.Enum):
    QUOTE = "quote"
    INVOICE = "invoice"
    RECEIPT = "receipt"


class OrgMemberRole(str, enum.Enum):
    ORG_ADMIN = "org_admin"
    LEARNER = "learner"
    CONTRACTOR = "contractor"  # 契約者（受講しない場合あり）


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"
    PII_DELETED = "pii_deleted"


class ContentFormat(str, enum.Enum):
    VIDEO = "video"
    PDF = "pdf"
    TEXT = "text"
    SCORM = "scorm"


class ShippingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    PICKING = "picking"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"
    RESHIPPED = "reshipped"
    CANCELLED = "cancelled"


class StockMoveType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    ADJUST = "adjust"
    RETURN = "return"


# --- 申込・契約 ---
class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    discount_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizationMembership(Base):
    """一人が複数企業に所属可能."""

    __tablename__ = "organization_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[OrgMemberRole] = mapped_column(
        _enum(OrgMemberRole, "orgmemberrole", native=False), default=OrgMemberRole.LEARNER
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    contract_type: Mapped[ContractType] = mapped_column(
        _enum(ContractType, "contracttype", native=False), default=ContractType.INDIVIDUAL
    )
    channel: Mapped[IntakeChannel] = mapped_column(
        _enum(IntakeChannel, "intakechannel", native=False), default=IntakeChannel.WEB
    )
    status: Mapped[ContractStatus] = mapped_column(
        _enum(ContractStatus, "contractstatus", native=False), default=ContractStatus.DRAFT
    )
    contractor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agency_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True
    )
    referral_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        _enum(PaymentMethod, "paymentmethod", native=False), default=PaymentMethod.LUMP_SUM
    )
    installment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContractItem(Base):
    """複数講座の同時申込."""

    __tablename__ = "contract_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    learner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class ContractChange(Base):
    """変更・キャンセル・解約."""

    __tablename__ = "contract_changes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    change_type: Mapped[str] = mapped_column(String(32))  # change / cancel / terminate
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InstallmentSchedule(Base):
    __tablename__ = "installment_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    installment_no: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BillingDocument(Base):
    """見積・請求書・領収書."""

    __tablename__ = "billing_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    doc_type: Mapped[DocumentType] = mapped_column(_enum(DocumentType, "documenttype", native=False))
    document_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# --- アカウント管理 ---
class FamilyLink(Base):
    """家族申込."""

    __tablename__ = "family_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guardian_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    member_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    relation: Mapped[str] = mapped_column(String(64), default="family")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountMerge(Base):
    """重複会員の統合."""

    __tablename__ = "account_merges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primary_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    merged_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    merged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class LoginIdHistory(Base):
    __tablename__ = "login_id_histories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    old_login_id: Mapped[str] = mapped_column(String(255))
    new_login_id: Mapped[str] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountLifecycle(Base):
    """退会・利用停止・個人情報削除."""

    __tablename__ = "account_lifecycles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[AccountStatus] = mapped_column(
        _enum(AccountStatus, "accountstatus", native=False), default=AccountStatus.ACTIVE
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# --- 学習管理 ---
class LearningContent(Base):
    """動画 / PDF / テキスト / SCORM."""

    __tablename__ = "learning_contents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[ContentFormat] = mapped_column(_enum(ContentFormat, "contentformat", native=False))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    content_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scorm_package_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    offline_available: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentPrerequisite(Base):
    """前提科目・学習順序."""

    __tablename__ = "content_prerequisites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_contents.id", ondelete="CASCADE"), index=True
    )
    prerequisite_content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_contents.id", ondelete="CASCADE"), index=True
    )


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_contents.id", ondelete="CASCADE"), index=True
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_contents.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComprehensionQuiz(Base):
    __tablename__ = "comprehension_quizzes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_contents.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    passing_score: Mapped[int] = mapped_column(Integer, default=70)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)  # 再受験
    questions: Mapped[list] = mapped_column(JSONB, default=list)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprehension_quizzes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningReminder(Base):
    """未受講者への督促."""

    __tablename__ = "learning_reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(32), default="email")
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


# --- 通信教育・教材発送 ---
class MaterialEdition(Base):
    """教材改訂時の版管理."""

    __tablename__ = "material_editions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    edition: Mapped[str] = mapped_column(String(32))  # e.g. 2026-A
    revised_at: Mapped[date] = mapped_column(Date)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    edition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material_editions.id", ondelete="SET NULL"), nullable=True
    )
    warehouse: Mapped[str] = mapped_column(String(64), default="main")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), index=True
    )
    move_type: Mapped[StockMoveType] = mapped_column(_enum(StockMoveType, "stockmovetype", native=False))
    quantity: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(64), default="home")
    postal_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="JP")
    prefecture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str] = mapped_column(String(128))
    address_line: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShippingOrder(Base):
    """紙教材発送（分割発送・海外対応）."""

    __tablename__ = "shipping_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    address_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipping_addresses.id", ondelete="RESTRICT"))
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"))
    edition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material_editions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ShippingStatus] = mapped_column(
        _enum(ShippingStatus, "shippingstatus", native=False), default=ShippingStatus.SCHEDULED
    )
    scheduled_ship_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    split_group: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 分割発送グループ
    split_sequence: Mapped[int] = mapped_column(Integer, default=1)
    is_overseas: Mapped[bool] = mapped_column(Boolean, default=False)
    tracking_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parent_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipping_orders.id", ondelete="SET NULL"), nullable=True
    )  # 再発送元
    return_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BundleProduct(Base):
    """eラーニングとのセット商品."""

    __tablename__ = "bundle_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
