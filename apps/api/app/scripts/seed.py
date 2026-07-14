"""デモカタログを不足分だけ追加（既存行は更新しない）."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, text

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, Base, engine
from app.models import domain as _domain  # noqa: F401
from app.models.domain import (
    Application,
    ApplicationStatus,
    AssignmentSubmission,
    AudienceType,
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    Exam,
    ExamStatus,
    FaqArticle,
    Inquiry,
    InquiryStatus,
    Lesson,
    Material,
    MaterialType,
    MediaContent,
    MediaType,
    ServiceType,
    User,
    UserRole,
)


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_name VARCHAR(255)",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS service_types VARCHAR[] DEFAULT '{}'",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS price NUMERIC(12,2)",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS qualification_name VARCHAR(255)",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS draft_started_at TIMESTAMPTZ",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS audience VARCHAR(32) DEFAULT 'individual'",
            "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS has_correction BOOLEAN DEFAULT FALSE",
            "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS renewed_at TIMESTAMPTZ",
            "ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS corrector_id UUID",
            "ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS turnaround_hours INTEGER",
        ]:
            await conn.execute(text(stmt))


async def ensure_user(db, email: str, full_name: str, role: UserRole, org: str | None = None) -> User:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        role=role,
        organization_name=org,
        hashed_password=get_password_hash("password123"),
    )
    db.add(user)
    await db.flush()
    return user


async def seed() -> None:
    await migrate()
    async with AsyncSessionLocal() as db:
        admin = await ensure_user(db, "admin@example.com", "管理者", UserRole.ADMIN)
        await ensure_user(db, "corrector@example.com", "添削担当", UserRole.CORRECTOR)
        learner = await ensure_user(db, "learner@example.com", "受講者 太郎", UserRole.LEARNER)
        await ensure_user(db, "corp@example.com", "法人担当 花子", UserRole.CORPORATE_MANAGER, "サンプル株式会社")
        _ = admin

        now = datetime.now(UTC)
        specs = [
            (
                "PERS-001",
                "ビジネス基礎通信講座",
                "個人向け通信教育。紙教材＋添削で基礎力を養成します。",
                AudienceType.INDIVIDUAL,
                [ServiceType.PERSONAL.value, ServiceType.PAPER.value, ServiceType.CORRECTION.value],
                Decimal("39800"),
                None,
                90,
                21,
                14,
            ),
            (
                "CORP-001",
                "法人向けリーダーシップ研修",
                "法人研修向け。動画ライブ＋修了認定付き。",
                AudienceType.CORPORATE,
                [ServiceType.CORPORATE.value, ServiceType.VIDEO_LIVE.value, ServiceType.EXAM_CERT.value],
                Decimal("120000"),
                None,
                30,
                10,
                5,
            ),
            (
                "QUAL-001",
                "簿記3級 資格対策講座",
                "資格講座。動画・試験・修了認定を統合。",
                AudienceType.BOTH,
                [
                    ServiceType.QUALIFICATION.value,
                    ServiceType.VIDEO_LIVE.value,
                    ServiceType.EXAM_CERT.value,
                    ServiceType.PAPER.value,
                ],
                Decimal("19800"),
                "日商簿記3級",
                60,
                30,
                20,
            ),
            (
                "DRAFT-001",
                "新商品: DXリテラシー（準備中）",
                "商品投入期間短縮の対象ドラフト。",
                AudienceType.BOTH,
                [ServiceType.CORPORATE.value, ServiceType.VIDEO_LIVE.value],
                Decimal("50000"),
                None,
                14,
                2,
                None,
            ),
        ]

        courses: dict[str, Course] = {}
        for code, title, desc, audience, services, price, qual, days, draft_ago, pub_ago in specs:
            course = (await db.execute(select(Course).where(Course.code == code))).scalar_one_or_none()
            if course is None:
                course = Course(
                    code=code,
                    title=title,
                    description=desc,
                    status=CourseStatus.DRAFT if pub_ago is None else CourseStatus.PUBLISHED,
                    audience=audience,
                    service_types=services,
                    duration_days=days,
                    price=price,
                    qualification_name=qual,
                    draft_started_at=now - timedelta(days=draft_ago),
                    published_at=(now - timedelta(days=pub_ago)) if pub_ago is not None else None,
                )
                db.add(course)
                await db.flush()
            else:
                # 既存行にサービス属性を補完
                if not course.service_types:
                    course.service_types = services
                if course.price is None:
                    course.price = price
                if course.draft_started_at is None:
                    course.draft_started_at = now - timedelta(days=draft_ago)
                if pub_ago is not None and course.published_at is None:
                    course.published_at = now - timedelta(days=pub_ago)
                    course.status = CourseStatus.PUBLISHED
            courses[code] = course

        personal, corporate, qual = courses["PERS-001"], courses["CORP-001"], courses["QUAL-001"]

        if not (await db.execute(select(Lesson).where(Lesson.course_id == personal.id))).scalars().first():
            db.add(
                Lesson(
                    course_id=personal.id,
                    title="第1回 ビジネス文書の書き方",
                    content="挨拶文・報告文の基本",
                    sort_order=1,
                    has_correction=True,
                )
            )

        if not (await db.execute(select(Material).where(Material.course_id == personal.id))).scalars().first():
            db.add(
                Material(
                    course_id=personal.id,
                    title="テキスト第1分冊",
                    material_type=MaterialType.PAPER,
                    shipping_required=True,
                    stock_quantity=500,
                )
            )
        if not (await db.execute(select(Material).where(Material.course_id == qual.id))).scalars().first():
            db.add(
                Material(
                    course_id=qual.id,
                    title="簿記問題集 PDF",
                    material_type=MaterialType.PDF,
                    shipping_required=False,
                    download_url="https://example.com/boki.pdf",
                )
            )
        if not (await db.execute(select(MediaContent).where(MediaContent.course_id == corporate.id))).scalars().first():
            db.add(
                MediaContent(
                    course_id=corporate.id,
                    title="キックオフ・ライブ",
                    media_type=MediaType.LIVE,
                    stream_url="https://example.com/live/kickoff",
                    scheduled_at=now + timedelta(days=3),
                )
            )
        if not (await db.execute(select(MediaContent).where(MediaContent.course_id == qual.id))).scalars().first():
            db.add(
                MediaContent(
                    course_id=qual.id,
                    title="仕訳の基礎 VOD",
                    media_type=MediaType.VOD,
                    stream_url="https://example.com/vod/shiwake",
                    duration_seconds=1800,
                )
            )
        if not (await db.execute(select(Exam).where(Exam.course_id == qual.id))).scalars().first():
            db.add(
                Exam(
                    course_id=qual.id,
                    title="簿記3級 模擬試験",
                    passing_score=70,
                    status=ExamStatus.OPEN,
                    questions=[
                        {"id": "q1", "text": "借方は左側か？", "answer": "yes"},
                        {"id": "q2", "text": "現金は資産か？", "answer": "yes"},
                        {"id": "q3", "text": "借入金は資産か？", "answer": "no"},
                    ],
                )
            )

        if not (await db.execute(select(Application).limit(1))).scalars().first():
            db.add_all(
                [
                    Application(
                        course_id=personal.id,
                        email=learner.email,
                        full_name=learner.full_name,
                        status=ApplicationStatus.CONVERTED,
                        source="web",
                        user_id=learner.id,
                        converted_at=now - timedelta(days=7),
                    ),
                    Application(
                        course_id=qual.id,
                        email="prospect@example.com",
                        full_name="検討中 次郎",
                        status=ApplicationStatus.APPLIED,
                        source="ads",
                    ),
                ]
            )

        enroll = (
            await db.execute(
                select(Enrollment).where(Enrollment.user_id == learner.id, Enrollment.course_id == personal.id)
            )
        ).scalar_one_or_none()
        if enroll is None:
            enroll = Enrollment(
                user_id=learner.id,
                course_id=personal.id,
                status=EnrollmentStatus.ACTIVE,
                progress_percent=40,
            )
            db.add(enroll)
            await db.flush()

        if not (
            await db.execute(
                select(Enrollment).where(Enrollment.user_id == learner.id, Enrollment.course_id == qual.id)
            )
        ).scalar_one_or_none():
            db.add(
                Enrollment(
                    user_id=learner.id,
                    course_id=qual.id,
                    status=EnrollmentStatus.ACTIVE,
                    progress_percent=80,
                )
            )

        if not (
            await db.execute(select(AssignmentSubmission).where(AssignmentSubmission.enrollment_id == enroll.id))
        ).scalars().first():
            db.add(
                AssignmentSubmission(
                    enrollment_id=enroll.id,
                    title="第1回レポート",
                    body="ビジネス文書の練習提出です。",
                    status="submitted",
                )
            )

        if not (await db.execute(select(FaqArticle).limit(1))).scalars().first():
            db.add_all(
                [
                    FaqArticle(
                        category="enrollment",
                        question="申込後いつから受講できますか？",
                        answer="お申込完了後、即時マイページから受講を開始できます。",
                        view_count=120,
                        helpful_count=45,
                    ),
                    FaqArticle(
                        category="correction",
                        question="添削の返却目安は？",
                        answer="通常3〜5営業日で返却します。",
                        view_count=80,
                        helpful_count=30,
                    ),
                ]
            )
        if not (await db.execute(select(Inquiry).limit(1))).scalars().first():
            db.add_all(
                [
                    Inquiry(
                        email="prospect@example.com",
                        subject="開講日について",
                        body="いつから始められますか？",
                        category="enrollment",
                        status=InquiryStatus.CLOSED,
                        resolved_by_faq=True,
                        answered_at=now - timedelta(days=2),
                    ),
                    Inquiry(
                        email="other@example.com",
                        subject="法人契約の人数上限",
                        body="50名で契約できますか？",
                        category="corporate",
                        status=InquiryStatus.OPEN,
                    ),
                ]
            )

        await db.commit()
        print("Seed upsert completed.")


if __name__ == "__main__":
    asyncio.run(seed())
