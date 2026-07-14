"""申込・契約 / アカウント / 学習 / 発送 のスキーマ."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.platform import (
    AccountStatus,
    ContentFormat,
    ContractStatus,
    ContractType,
    DocumentType,
    IntakeChannel,
    OrgMemberRole,
    PaymentMethod,
    ShippingStatus,
    StockMoveType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Coupons / Contracts ---
class CouponCreate(BaseModel):
    code: str
    name: str
    discount_percent: int | None = None
    discount_amount: Decimal | None = None
    campaign_name: str | None = None


class CouponRead(ORMModel):
    id: UUID
    code: str
    name: str
    discount_percent: int | None
    discount_amount: Decimal | None
    campaign_name: str | None
    is_active: bool


class ContractItemIn(BaseModel):
    course_id: UUID
    learner_user_id: UUID | None = None
    unit_price: Decimal = Decimal("0")
    start_date: date | None = None
    end_date: date | None = None


class ContractCreate(BaseModel):
    contract_type: ContractType = ContractType.INDIVIDUAL
    channel: IntakeChannel = IntakeChannel.WEB
    organization_id: UUID | None = None
    agency_name: str | None = None
    coupon_code: str | None = None
    referral_code: str | None = None
    campaign_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    payment_method: PaymentMethod = PaymentMethod.LUMP_SUM
    installment_count: int | None = Field(default=None, ge=2, le=24)
    items: list[ContractItemIn] = Field(min_length=1)
    notes: str | None = None


class ContractItemRead(ORMModel):
    id: UUID
    course_id: UUID
    learner_user_id: UUID | None
    enrollment_id: UUID | None
    unit_price: Decimal
    start_date: date | None
    end_date: date | None


class ContractRead(ORMModel):
    id: UUID
    contract_no: str
    contract_type: ContractType
    channel: IntakeChannel
    status: ContractStatus
    contractor_user_id: UUID | None
    organization_id: UUID | None
    agency_name: str | None
    referral_code: str | None
    campaign_name: str | None
    start_date: date | None
    end_date: date | None
    payment_method: PaymentMethod
    installment_count: int | None
    total_amount: Decimal
    discount_amount: Decimal
    created_at: datetime


class ContractChangeCreate(BaseModel):
    change_type: str = Field(pattern="^(change|cancel|terminate)$")
    reason: str | None = None
    effective_date: date | None = None


class InstallmentRead(ORMModel):
    id: UUID
    installment_no: int
    due_date: date
    amount: Decimal
    paid: bool


class DocumentRead(ORMModel):
    id: UUID
    contract_id: UUID
    doc_type: DocumentType
    document_no: str
    amount: Decimal
    issued_at: datetime


class DocumentIssue(BaseModel):
    doc_type: DocumentType


# --- Organizations / Accounts ---
class OrganizationCreate(BaseModel):
    name: str
    code: str
    billing_email: EmailStr | None = None


class OrganizationRead(ORMModel):
    id: UUID
    name: str
    code: str
    billing_email: str | None
    is_active: bool


class MembershipCreate(BaseModel):
    user_id: UUID
    role: OrgMemberRole = OrgMemberRole.LEARNER
    is_primary: bool = False


class MembershipRead(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: OrgMemberRole
    is_primary: bool


class FamilyLinkCreate(BaseModel):
    member_user_id: UUID
    relation: str = "family"


class FamilyLinkRead(ORMModel):
    id: UUID
    guardian_user_id: UUID
    member_user_id: UUID
    relation: str


class AccountMergeCreate(BaseModel):
    primary_user_id: UUID
    merged_user_id: UUID
    reason: str | None = None


class LoginIdChange(BaseModel):
    new_login_id: str = Field(min_length=3, max_length=255)


class AccountStatusUpdate(BaseModel):
    status: AccountStatus
    reason: str | None = None


class UserAccountRead(ORMModel):
    id: UUID
    email: EmailStr | None
    full_name: str
    role: str
    login_id: str | None
    is_contractor: bool
    account_status: str
    organization_name: str | None
    phone: str | None
    is_active: bool


# --- Learning ---
class LearningContentCreate(BaseModel):
    course_id: UUID
    title: str
    format: ContentFormat
    sort_order: int = 0
    content_url: str | None = None
    scorm_package_url: str | None = None
    offline_available: bool = False
    duration_minutes: int | None = None
    prerequisite_content_ids: list[UUID] = Field(default_factory=list)


class LearningContentRead(ORMModel):
    id: UUID
    course_id: UUID
    title: str
    format: ContentFormat
    sort_order: int
    content_url: str | None
    scorm_package_url: str | None
    offline_available: bool
    duration_minutes: int | None


class ProgressUpdate(BaseModel):
    enrollment_id: UUID
    content_id: UUID
    progress_percent: int = Field(ge=0, le=100)
    deadline_at: datetime | None = None


class ProgressRead(ORMModel):
    id: UUID
    enrollment_id: UUID
    content_id: UUID
    progress_percent: int
    completed: bool
    deadline_at: datetime | None


class BookmarkCreate(BaseModel):
    content_id: UUID
    note: str | None = None


class BookmarkRead(ORMModel):
    id: UUID
    user_id: UUID
    content_id: UUID
    note: str | None


class QuizCreate(BaseModel):
    content_id: UUID
    title: str
    passing_score: int = 70
    max_attempts: int = 3
    questions: list[dict] = Field(default_factory=list)


class QuizRead(ORMModel):
    id: UUID
    content_id: UUID
    title: str
    passing_score: int
    max_attempts: int
    questions: list


class QuizSubmit(BaseModel):
    answers: dict[str, str]


class QuizAttemptRead(ORMModel):
    id: UUID
    quiz_id: UUID
    score: int | None
    passed: bool
    attempt_no: int
    submitted_at: datetime


class ReminderCreate(BaseModel):
    enrollment_id: UUID
    message: str
    channel: str = "email"


class ReminderRead(ORMModel):
    id: UUID
    enrollment_id: UUID
    channel: str
    message: str
    sent_at: datetime
    acknowledged: bool


# --- Shipping ---
class AddressCreate(BaseModel):
    label: str = "home"
    postal_code: str
    country: str = "JP"
    prefecture: str | None = None
    city: str
    address_line: str
    phone: str | None = None
    is_default: bool = True


class AddressRead(ORMModel):
    id: UUID
    user_id: UUID
    label: str
    postal_code: str
    country: str
    prefecture: str | None
    city: str
    address_line: str
    phone: str | None
    is_default: bool


class EditionCreate(BaseModel):
    material_id: UUID
    edition: str
    revised_at: date
    change_summary: str | None = None
    is_current: bool = True


class EditionRead(ORMModel):
    id: UUID
    material_id: UUID
    edition: str
    revised_at: date
    change_summary: str | None
    is_current: bool


class InventoryAdjust(BaseModel):
    material_id: UUID
    edition_id: UUID | None = None
    warehouse: str = "main"
    quantity_delta: int
    move_type: StockMoveType = StockMoveType.ADJUST
    note: str | None = None


class InventoryRead(ORMModel):
    id: UUID
    material_id: UUID
    edition_id: UUID | None
    warehouse: str
    quantity: int


class ShippingCreate(BaseModel):
    address_id: UUID
    material_id: UUID
    edition_id: UUID | None = None
    enrollment_id: UUID | None = None
    contract_id: UUID | None = None
    scheduled_ship_date: date | None = None
    split_group: str | None = None
    split_sequence: int = 1
    is_overseas: bool = False


class ShippingRead(ORMModel):
    id: UUID
    status: ShippingStatus
    material_id: UUID
    address_id: UUID
    scheduled_ship_date: date | None
    shipped_at: datetime | None
    split_group: str | None
    split_sequence: int
    is_overseas: bool
    tracking_no: str | None
    parent_order_id: UUID | None


class ShippingAction(BaseModel):
    tracking_no: str | None = None
    return_reason: str | None = None


class BundleCreate(BaseModel):
    code: str
    name: str
    course_id: UUID
    material_id: UUID
    price: Decimal


class BundleRead(ORMModel):
    id: UUID
    code: str
    name: str
    course_id: UUID
    material_id: UUID
    price: Decimal
    is_active: bool
