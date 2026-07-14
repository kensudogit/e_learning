from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.domain import (
    ApplicationStatus,
    AttemptStatus,
    AudienceType,
    CourseStatus,
    EnrollmentStatus,
    ExamStatus,
    InquiryStatus,
    MaterialType,
    MediaType,
    ServiceType,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    role: UserRole = UserRole.LEARNER
    organization_name: str | None = None


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    organization_name: str | None
    login_id: str | None = None
    is_contractor: bool = False
    account_status: str = "active"
    phone: str | None = None
    is_active: bool
    created_at: datetime


# --- Course ---
class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    duration_days: int | None = None
    status: CourseStatus = CourseStatus.DRAFT
    audience: AudienceType = AudienceType.INDIVIDUAL
    service_types: list[ServiceType] = Field(default_factory=list)
    price: Decimal | None = None
    qualification_name: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_days: int | None = None
    status: CourseStatus | None = None
    audience: AudienceType | None = None
    service_types: list[ServiceType] | None = None
    price: Decimal | None = None
    qualification_name: str | None = None


class CourseRead(ORMModel):
    id: UUID
    code: str
    title: str
    description: str | None
    status: CourseStatus
    audience: AudienceType
    service_types: list[str]
    duration_days: int | None
    price: Decimal | None
    qualification_name: str | None
    draft_started_at: datetime | None
    published_at: datetime | None
    created_at: datetime


class LessonCreate(BaseModel):
    title: str
    content: str | None = None
    sort_order: int = 0
    has_correction: bool = False


class LessonRead(ORMModel):
    id: UUID
    course_id: UUID
    title: str
    content: str | None
    sort_order: int
    has_correction: bool


# --- Enrollment ---
class EnrollmentCreate(BaseModel):
    course_id: UUID


class EnrollmentRead(ORMModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    status: EnrollmentStatus
    enrolled_at: datetime
    completed_at: datetime | None
    renewed_at: datetime | None
    progress_percent: int


class EnrollmentProgressUpdate(BaseModel):
    progress_percent: int = Field(ge=0, le=100)
    status: EnrollmentStatus | None = None


# --- Application (申込) ---
class ApplicationCreate(BaseModel):
    course_id: UUID
    email: EmailStr
    full_name: str
    organization_name: str | None = None
    source: str | None = "web"


class ApplicationRead(ORMModel):
    id: UUID
    user_id: UUID | None
    course_id: UUID
    email: EmailStr
    full_name: str
    organization_name: str | None
    status: ApplicationStatus
    source: str | None
    created_at: datetime
    converted_at: datetime | None


# --- Assignment ---
class AssignmentSubmit(BaseModel):
    enrollment_id: UUID
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    assignment_id: UUID | None = None  # 課題マスタ（任意）


class AssignmentFeedback(BaseModel):
    feedback: str = Field(min_length=1)
    status: str = "returned"
    score: int | None = Field(default=None, ge=0, le=100)
    assignment_id: UUID | None = None


class AssignmentMasterRead(ORMModel):
    id: UUID
    course_id: UUID
    code: str
    title: str
    description: str | None
    max_score: int
    requires_correction: bool
    due_days: int | None = None


class CorrectionResultRead(ORMModel):
    id: UUID
    assignment_id: UUID | None
    submission_id: UUID | None
    enrollment_id: UUID
    corrector_id: UUID | None
    score: int | None
    status: str
    feedback: str | None
    turnaround_hours: int | None
    corrected_at: datetime


class AssignmentRead(ORMModel):
    id: UUID
    enrollment_id: UUID
    title: str
    body: str
    status: str
    feedback: str | None
    corrector_id: UUID | None = None
    submitted_at: datetime
    reviewed_at: datetime | None
    turnaround_hours: int | None = None


class LearningHistoryRead(ORMModel):
    id: UUID
    enrollment_id: UUID
    event_type: str
    title: str
    detail: str | None
    occurred_at: datetime


# --- Material ---
class MaterialCreate(BaseModel):
    course_id: UUID
    title: str
    material_type: MaterialType = MaterialType.PAPER
    shipping_required: bool = True
    stock_quantity: int | None = None
    download_url: str | None = None


class MaterialRead(ORMModel):
    id: UUID
    course_id: UUID
    title: str
    material_type: MaterialType
    shipping_required: bool
    stock_quantity: int | None
    download_url: str | None


# --- Media ---
class MediaCreate(BaseModel):
    course_id: UUID
    title: str
    media_type: MediaType = MediaType.VOD
    stream_url: str | None = None
    duration_seconds: int | None = None
    scheduled_at: datetime | None = None
    is_live_now: bool = False


class MediaRead(ORMModel):
    id: UUID
    course_id: UUID
    title: str
    media_type: MediaType
    stream_url: str | None
    duration_seconds: int | None
    scheduled_at: datetime | None
    is_live_now: bool


# --- Exam / Certificate ---
class ExamCreate(BaseModel):
    course_id: UUID
    title: str
    passing_score: int = 70
    status: ExamStatus = ExamStatus.OPEN
    questions: list[dict] = Field(default_factory=list)


class ExamRead(ORMModel):
    id: UUID
    course_id: UUID
    title: str
    passing_score: int
    status: ExamStatus
    questions: list
    created_at: datetime


class ExamSubmit(BaseModel):
    enrollment_id: UUID
    answers: dict[str, str]


class ExamAttemptRead(ORMModel):
    id: UUID
    exam_id: UUID
    enrollment_id: UUID
    score: int | None
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None


class CertificateRead(ORMModel):
    id: UUID
    enrollment_id: UUID
    certificate_no: str
    title: str
    issued_at: datetime


class CertificateIssue(BaseModel):
    enrollment_id: UUID
    title: str | None = None


# --- Inquiry / FAQ ---
class InquiryCreate(BaseModel):
    email: EmailStr
    subject: str
    body: str
    category: str = "general"


class InquiryRead(ORMModel):
    id: UUID
    email: EmailStr
    subject: str
    body: str
    category: str
    status: InquiryStatus
    resolved_by_faq: bool
    answer: str | None
    created_at: datetime
    answered_at: datetime | None


class InquiryAnswer(BaseModel):
    answer: str
    status: InquiryStatus = InquiryStatus.ANSWERED


class FaqCreate(BaseModel):
    category: str
    question: str
    answer: str


class FaqRead(ORMModel):
    id: UUID
    category: str
    question: str
    answer: str
    view_count: int
    helpful_count: int
    is_published: bool


# --- KPI ---
class KpiDashboard(BaseModel):
    learner_count: int
    active_enrollments: int
    application_count: int
    converted_applications: int
    conversion_rate: float
    retention_rate: float
    renewed_enrollments: int
    inquiry_count: int
    inquiry_faq_resolved_rate: float
    open_inquiries: int
    pending_corrections: int
    avg_correction_turnaround_hours: float | None
    avg_product_launch_days: float | None
    published_courses: int
    draft_courses: int
    by_service_type: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
