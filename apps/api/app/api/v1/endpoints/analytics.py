from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import (
    Application,
    ApplicationStatus,
    AssignmentSubmission,
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    Inquiry,
    InquiryStatus,
    User,
    UserRole,
)
from app.schemas import KpiDashboard

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpi", response_model=KpiDashboard)
async def get_kpi_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiDashboard:
    """経営 KPI: 受講者数 / 申込転換率 / 継続率 / 問い合わせ削減 / 運用工数 / 商品投入期間."""
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.CORPORATE_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="KPI 閲覧権限がありません")

    learner_count = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.LEARNER))
    ).scalar_one()

    active_enrollments = (
        await db.execute(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.RENEWED]))
        )
    ).scalar_one()

    application_count = (await db.execute(select(func.count()).select_from(Application))).scalar_one()
    converted_applications = (
        await db.execute(
            select(func.count()).select_from(Application).where(Application.status == ApplicationStatus.CONVERTED)
        )
    ).scalar_one()
    conversion_rate = (converted_applications / application_count * 100) if application_count else 0.0

    total_enrollments = (await db.execute(select(func.count()).select_from(Enrollment))).scalar_one()
    renewed = (
        await db.execute(
            select(func.count()).select_from(Enrollment).where(Enrollment.status == EnrollmentStatus.RENEWED)
        )
    ).scalar_one()
    completed_or_renewed = (
        await db.execute(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.status.in_([EnrollmentStatus.COMPLETED, EnrollmentStatus.RENEWED]))
        )
    ).scalar_one()
    retention_rate = (completed_or_renewed / total_enrollments * 100) if total_enrollments else 0.0

    inquiry_count = (await db.execute(select(func.count()).select_from(Inquiry))).scalar_one()
    faq_resolved = (
        await db.execute(select(func.count()).select_from(Inquiry).where(Inquiry.resolved_by_faq.is_(True)))
    ).scalar_one()
    open_inquiries = (
        await db.execute(
            select(func.count()).select_from(Inquiry).where(Inquiry.status == InquiryStatus.OPEN)
        )
    ).scalar_one()
    inquiry_faq_resolved_rate = (faq_resolved / inquiry_count * 100) if inquiry_count else 0.0

    pending_corrections = (
        await db.execute(
            select(func.count())
            .select_from(AssignmentSubmission)
            .where(AssignmentSubmission.status.in_(["submitted", "reviewing"]))
        )
    ).scalar_one()
    avg_turnaround = (
        await db.execute(
            select(func.avg(AssignmentSubmission.turnaround_hours)).where(
                AssignmentSubmission.turnaround_hours.is_not(None)
            )
        )
    ).scalar_one()

    published_courses = (
        await db.execute(
            select(func.count()).select_from(Course).where(Course.status == CourseStatus.PUBLISHED)
        )
    ).scalar_one()
    draft_courses = (
        await db.execute(select(func.count()).select_from(Course).where(Course.status == CourseStatus.DRAFT))
    ).scalar_one()

    # 商品投入期間: draft_started_at → published_at の平均日数
    published = (
        await db.execute(
            select(Course).where(
                Course.status == CourseStatus.PUBLISHED,
                Course.published_at.is_not(None),
                Course.draft_started_at.is_not(None),
            )
        )
    ).scalars().all()
    launch_days: list[float] = []
    for c in published:
        if c.published_at and c.draft_started_at:
            delta = (c.published_at - c.draft_started_at).total_seconds() / 86400
            launch_days.append(max(0.0, delta))
    avg_product_launch_days = sum(launch_days) / len(launch_days) if launch_days else None

    courses = (await db.execute(select(Course))).scalars().all()
    by_service: dict[str, int] = {}
    for c in courses:
        for st in c.service_types or []:
            by_service[st] = by_service.get(st, 0) + 1

    return KpiDashboard(
        learner_count=learner_count,
        active_enrollments=active_enrollments,
        application_count=application_count,
        converted_applications=converted_applications,
        conversion_rate=round(conversion_rate, 2),
        retention_rate=round(retention_rate, 2),
        renewed_enrollments=renewed,
        inquiry_count=inquiry_count,
        inquiry_faq_resolved_rate=round(inquiry_faq_resolved_rate, 2),
        open_inquiries=open_inquiries,
        pending_corrections=pending_corrections,
        avg_correction_turnaround_hours=round(float(avg_turnaround), 2) if avg_turnaround is not None else None,
        avg_product_launch_days=round(avg_product_launch_days, 2) if avg_product_launch_days is not None else None,
        published_courses=published_courses,
        draft_courses=draft_courses,
        by_service_type=by_service,
    )
