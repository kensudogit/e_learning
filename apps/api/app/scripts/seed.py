"""デモカタログを不足分だけ追加（既存行は更新しない）."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, Base, engine
from app.models import domain as _domain  # noqa: F401
from app.models import platform as _platform  # noqa: F401
from app.models import core_entities as _core  # noqa: F401
from app.models.core_entities import (
    Assignment,
    CorrectionResult,
    Curriculum,
    CurriculumItem,
    Customer,
    CustomerType,
    Grade,
    GradeSource,
    Learner,
    LearningHistory,
    Payment,
    PaymentStatus,
    Product,
    ProductType,
)
from app.models.domain import (
    Application,
    ApplicationStatus,
    AssignmentSubmission,
    AudienceType,
    Certificate,
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
from app.models.platform import (
    BillingDocument,
    BundleProduct,
    ComprehensionQuiz,
    ContentFormat,
    ContentPrerequisite,
    Contract,
    ContractItem,
    ContractStatus,
    ContractType,
    Coupon,
    DocumentType,
    IntakeChannel,
    InventoryItem,
    LearningContent,
    LearningProgress,
    MaterialEdition,
    Organization,
    OrganizationMembership,
    OrgMemberRole,
    PaymentMethod,
    FamilyLink,
    ShippingAddress,
    ShippingOrder,
    ShippingStatus,
    StockMoveType,
    StockMovement,
)


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_name VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_id VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(32) DEFAULT 'active'",
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
        user.hashed_password = get_password_hash("password123")
        user.full_name = full_name
        user.role = role
        if org:
            user.organization_name = org
        user.is_active = True
        await db.flush()
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


async def first_or_none(db, stmt):
    return (await db.execute(stmt.limit(1))).scalars().first()


async def seed() -> None:
    await migrate()
    async with AsyncSessionLocal() as db:
        admin = await ensure_user(db, "admin@example.com", "管理者", UserRole.ADMIN)
        await ensure_user(db, "corrector@example.com", "添削担当", UserRole.CORRECTOR)
        learner = await ensure_user(db, "learner@example.com", "受講者 太郎", UserRole.LEARNER)
        family_member = await ensure_user(db, "family@example.com", "受講者 次郎", UserRole.LEARNER)
        corp = await ensure_user(
            db, "corp@example.com", "法人担当 花子", UserRole.CORPORATE_MANAGER, "サンプル株式会社"
        )
        _ = admin

        if not await first_or_none(
            db,
            select(FamilyLink).where(
                FamilyLink.guardian_user_id == learner.id,
                FamilyLink.member_user_id == family_member.id,
            ),
        ):
            db.add(
                FamilyLink(
                    guardian_user_id=learner.id,
                    member_user_id=family_member.id,
                    relation="子",
                )
            )
            await db.flush()
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
            course = await first_or_none(db, select(Course).where(Course.code == code))
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

        if not await first_or_none(db, select(Lesson).where(Lesson.course_id == personal.id)):
            db.add(
                Lesson(
                    course_id=personal.id,
                    title="第1回 ビジネス文書の書き方",
                    content="挨拶文・報告文の基本",
                    sort_order=1,
                    has_correction=True,
                )
            )

        paper_material = await first_or_none(db, select(Material).where(Material.course_id == personal.id))
        if paper_material is None:
            paper_material = Material(
                course_id=personal.id,
                title="テキスト第1分冊",
                material_type=MaterialType.PAPER,
                shipping_required=True,
                stock_quantity=500,
            )
            db.add(paper_material)
            await db.flush()

        if not await first_or_none(db, select(Material).where(Material.course_id == qual.id)):
            db.add(
                Material(
                    course_id=qual.id,
                    title="簿記問題集 PDF",
                    material_type=MaterialType.PDF,
                    shipping_required=False,
                    download_url="https://example.com/boki.pdf",
                )
            )
        if not await first_or_none(db, select(MediaContent).where(MediaContent.course_id == corporate.id)):
            db.add(
                MediaContent(
                    course_id=corporate.id,
                    title="キックオフ・ライブ",
                    media_type=MediaType.LIVE,
                    stream_url="https://example.com/live/kickoff",
                    scheduled_at=now + timedelta(days=3),
                )
            )
        if not await first_or_none(db, select(MediaContent).where(MediaContent.course_id == qual.id)):
            db.add(
                MediaContent(
                    course_id=qual.id,
                    title="仕訳の基礎 VOD",
                    media_type=MediaType.VOD,
                    stream_url="https://example.com/vod/shiwake",
                    duration_seconds=1800,
                )
            )
        if not await first_or_none(db, select(Exam).where(Exam.course_id == qual.id)):
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

        if not await first_or_none(db, select(Application)):
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

        enroll = await first_or_none(
            db, select(Enrollment).where(Enrollment.user_id == learner.id, Enrollment.course_id == personal.id)
        )
        if enroll is None:
            enroll = Enrollment(
                user_id=learner.id,
                course_id=personal.id,
                status=EnrollmentStatus.ACTIVE,
                progress_percent=40,
            )
            db.add(enroll)
            await db.flush()

        if not await first_or_none(
            db, select(Enrollment).where(Enrollment.user_id == learner.id, Enrollment.course_id == qual.id)
        ):
            db.add(
                Enrollment(
                    user_id=learner.id,
                    course_id=qual.id,
                    status=EnrollmentStatus.ACTIVE,
                    progress_percent=80,
                )
            )

        if not await first_or_none(
            db, select(AssignmentSubmission).where(AssignmentSubmission.enrollment_id == enroll.id)
        ):
            db.add(
                AssignmentSubmission(
                    enrollment_id=enroll.id,
                    title="第1回レポート",
                    body="ビジネス文書の練習提出です。",
                    status="submitted",
                )
            )

        if not await first_or_none(db, select(FaqArticle)):
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
        if not await first_or_none(db, select(Inquiry)):
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

        # --- プラットフォーム拡張データ ---
        coupon = await first_or_none(db, select(Coupon).where(Coupon.code == "WELCOME10"))
        if coupon is None:
            coupon = Coupon(
                code="WELCOME10",
                name="新規10%OFF",
                discount_percent=10,
                campaign_name="春のスタートキャンペーン",
                is_active=True,
            )
            db.add(coupon)
            await db.flush()

        org = await first_or_none(db, select(Organization).where(Organization.code == "SAMPLE-CORP"))
        if org is None:
            org = Organization(
                name="サンプル株式会社",
                code="SAMPLE-CORP",
                billing_email="billing@sample.example.com",
            )
            db.add(org)
            await db.flush()

        if not await first_or_none(
            db,
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == corp.id,
            ),
        ):
            db.add(
                OrganizationMembership(
                    organization_id=org.id,
                    user_id=corp.id,
                    role=OrgMemberRole.ORG_ADMIN,
                    is_primary=True,
                )
            )

        contract = await first_or_none(db, select(Contract).where(Contract.contract_no == "CT-DEMO-PERS-001"))
        if contract is None:
            contract = Contract(
                contract_no="CT-DEMO-PERS-001",
                contract_type=ContractType.INDIVIDUAL,
                channel=IntakeChannel.WEB,
                status=ContractStatus.ACTIVE,
                contractor_user_id=learner.id,
                coupon_id=coupon.id,
                campaign_name="春のスタートキャンペーン",
                start_date=date.today() - timedelta(days=14),
                end_date=date.today() + timedelta(days=76),
                payment_method=PaymentMethod.LUMP_SUM,
                total_amount=Decimal("35820"),
                discount_amount=Decimal("3980"),
                notes="デモ個人契約",
            )
            db.add(contract)
            await db.flush()
            db.add(
                ContractItem(
                    contract_id=contract.id,
                    course_id=personal.id,
                    learner_user_id=learner.id,
                    enrollment_id=enroll.id,
                    unit_price=Decimal("39800"),
                    start_date=contract.start_date,
                    end_date=contract.end_date,
                )
            )
            db.add(
                BillingDocument(
                    contract_id=contract.id,
                    doc_type=DocumentType.INVOICE,
                    document_no=f"INV-DEMO-{uuid4().hex[:6].upper()}",
                    amount=contract.total_amount,
                    payload={"title": "ビジネス基礎通信講座 請求書"},
                )
            )

        corp_contract = await first_or_none(
            db, select(Contract).where(Contract.contract_no == "CT-DEMO-CORP-001")
        )
        if corp_contract is None:
            corp_contract = Contract(
                contract_no="CT-DEMO-CORP-001",
                contract_type=ContractType.CORPORATE,
                channel=IntakeChannel.AGENCY,
                status=ContractStatus.ACTIVE,
                contractor_user_id=corp.id,
                organization_id=org.id,
                agency_name="東日本代理店",
                start_date=date.today() - timedelta(days=5),
                end_date=date.today() + timedelta(days=25),
                payment_method=PaymentMethod.INVOICE,
                total_amount=Decimal("120000"),
                discount_amount=Decimal("0"),
                notes="デモ法人契約",
            )
            db.add(corp_contract)
            await db.flush()
            db.add(
                ContractItem(
                    contract_id=corp_contract.id,
                    course_id=corporate.id,
                    learner_user_id=corp.id,
                    unit_price=Decimal("120000"),
                    start_date=corp_contract.start_date,
                    end_date=corp_contract.end_date,
                )
            )

        video = await first_or_none(
            db,
            select(LearningContent).where(
                LearningContent.course_id == personal.id,
                LearningContent.title == "オリエンテーション動画",
            ),
        )
        if video is None:
            video = LearningContent(
                course_id=personal.id,
                title="オリエンテーション動画",
                format=ContentFormat.VIDEO,
                sort_order=1,
                content_url="https://example.com/video/orient",
                offline_available=True,
                duration_minutes=15,
            )
            pdf = LearningContent(
                course_id=personal.id,
                title="テキストPDF第1章",
                format=ContentFormat.PDF,
                sort_order=2,
                content_url="https://example.com/pdf/ch1",
                offline_available=True,
                duration_minutes=40,
            )
            db.add_all([video, pdf])
            await db.flush()
            db.add(ContentPrerequisite(content_id=pdf.id, prerequisite_content_id=video.id))
            db.add(
                ComprehensionQuiz(
                    content_id=video.id,
                    title="オリエン理解度チェック",
                    passing_score=70,
                    max_attempts=3,
                    questions=[
                        {"id": "q1", "text": "受講開始はマイページからか？", "answer": "yes"},
                        {"id": "q2", "text": "添削提出は必須か？", "answer": "yes"},
                    ],
                )
            )
            db.add(
                LearningProgress(
                    enrollment_id=enroll.id,
                    content_id=video.id,
                    progress_percent=100,
                    completed=True,
                    last_accessed_at=now - timedelta(days=1),
                )
            )
            db.add(
                LearningProgress(
                    enrollment_id=enroll.id,
                    content_id=pdf.id,
                    progress_percent=35,
                    completed=False,
                    last_accessed_at=now,
                    deadline_at=now + timedelta(days=14),
                )
            )

        address = await first_or_none(
            db, select(ShippingAddress).where(ShippingAddress.user_id == learner.id)
        )
        if address is None:
            address = ShippingAddress(
                user_id=learner.id,
                label="home",
                postal_code="100-0001",
                country="JP",
                prefecture="東京都",
                city="千代田区",
                address_line="丸の内1-1-1",
                phone="03-1234-5678",
                is_default=True,
            )
            db.add(address)
            await db.flush()

        edition = await first_or_none(
            db, select(MaterialEdition).where(MaterialEdition.material_id == paper_material.id)
        )
        if edition is None:
            edition = MaterialEdition(
                material_id=paper_material.id,
                edition="2026-A",
                revised_at=date.today() - timedelta(days=60),
                change_summary="最新ビジネス文書例を追加",
                is_current=True,
            )
            db.add(edition)
            await db.flush()

        inventory = await first_or_none(
            db, select(InventoryItem).where(InventoryItem.material_id == paper_material.id)
        )
        if inventory is None:
            inventory = InventoryItem(
                material_id=paper_material.id,
                edition_id=edition.id,
                warehouse="main",
                quantity=480,
            )
            db.add(inventory)
            await db.flush()
            db.add(
                StockMovement(
                    inventory_id=inventory.id,
                    move_type=StockMoveType.IN,
                    quantity=500,
                    note="初回入庫",
                )
            )
            db.add(
                StockMovement(
                    inventory_id=inventory.id,
                    move_type=StockMoveType.OUT,
                    quantity=20,
                    note="デモ出荷",
                )
            )

        if not await first_or_none(
            db, select(ShippingOrder).where(ShippingOrder.enrollment_id == enroll.id)
        ):
            db.add(
                ShippingOrder(
                    enrollment_id=enroll.id,
                    contract_id=contract.id if contract else None,
                    address_id=address.id,
                    material_id=paper_material.id,
                    edition_id=edition.id,
                    status=ShippingStatus.SCHEDULED,
                    scheduled_ship_date=date.today() + timedelta(days=2),
                    split_group="SPLIT-PERS-001",
                    split_sequence=1,
                    is_overseas=False,
                )
            )

        if not await first_or_none(db, select(BundleProduct).where(BundleProduct.code == "BUNDLE-PERS-PAPER")):
            db.add(
                BundleProduct(
                    code="BUNDLE-PERS-PAPER",
                    name="ビジネス基礎 通信+紙セット",
                    course_id=personal.id,
                    material_id=paper_material.id,
                    price=Decimal("44800"),
                )
            )

        # --- 主要テーブル（顧客・受講者・商品・カリキュラム・履歴・成績・課題・添削・入金） ---
        customer = await first_or_none(db, select(Customer).where(Customer.customer_no == "CUS-0001"))
        if customer is None:
            customer = Customer(
                customer_no="CUS-0001",
                customer_type=CustomerType.INDIVIDUAL,
                name=learner.full_name,
                email=learner.email,
                phone="03-1234-5678",
                user_id=learner.id,
                billing_address="東京都千代田区丸の内1-1-1",
            )
            db.add(customer)
            await db.flush()

        corp_customer = await first_or_none(db, select(Customer).where(Customer.customer_no == "CUS-CORP-001"))
        if corp_customer is None:
            corp_customer = Customer(
                customer_no="CUS-CORP-001",
                customer_type=CustomerType.CORPORATE,
                name="サンプル株式会社",
                email="billing@sample.example.com",
                user_id=corp.id,
                organization_id=org.id,
                billing_address="東京都港区芝1-1-1",
            )
            db.add(corp_customer)
            await db.flush()

        learner_master = await first_or_none(db, select(Learner).where(Learner.learner_no == "LRN-0001"))
        if learner_master is None:
            learner_master = Learner(
                learner_no="LRN-0001",
                user_id=learner.id,
                customer_id=customer.id,
                full_name=learner.full_name,
                email=learner.email,
            )
            db.add(learner_master)
            await db.flush()

        if not await first_or_none(db, select(Product).where(Product.product_code == "PRD-PERS-001")):
            db.add_all(
                [
                    Product(
                        product_code="PRD-PERS-001",
                        name="ビジネス基礎通信講座",
                        product_type=ProductType.COURSE,
                        course_id=personal.id,
                        list_price=Decimal("39800"),
                        description="個人向け通信教育パッケージ",
                    ),
                    Product(
                        product_code="PRD-BUNDLE-001",
                        name="ビジネス基礎 通信+紙セット",
                        product_type=ProductType.BUNDLE,
                        course_id=personal.id,
                        material_id=paper_material.id,
                        list_price=Decimal("44800"),
                    ),
                    Product(
                        product_code="PRD-QUAL-001",
                        name="簿記3級 資格対策講座",
                        product_type=ProductType.COURSE,
                        course_id=qual.id,
                        list_price=Decimal("19800"),
                    ),
                ]
            )

        curriculum = await first_or_none(db, select(Curriculum).where(Curriculum.code == "CUR-PERS-001"))
        if curriculum is None:
            curriculum = Curriculum(
                course_id=personal.id,
                code="CUR-PERS-001",
                title="ビジネス基礎 標準カリキュラム",
                version="2026.1",
                total_units=3,
                description="オリエン → テキスト → レポート",
                is_current=True,
            )
            db.add(curriculum)
            await db.flush()
            lesson1 = await first_or_none(db, select(Lesson).where(Lesson.course_id == personal.id))
            lc_video = await first_or_none(
                db,
                select(LearningContent).where(
                    LearningContent.course_id == personal.id,
                    LearningContent.title == "オリエンテーション動画",
                ),
            )
            items = []
            if lc_video:
                items.append(
                    CurriculumItem(
                        curriculum_id=curriculum.id,
                        sort_order=1,
                        item_type="learning_content",
                        learning_content_id=lc_video.id,
                        title=lc_video.title,
                    )
                )
            if lesson1:
                items.append(
                    CurriculumItem(
                        curriculum_id=curriculum.id,
                        sort_order=2,
                        item_type="lesson",
                        lesson_id=lesson1.id,
                        title=lesson1.title,
                    )
                )
            items.append(
                CurriculumItem(
                    curriculum_id=curriculum.id,
                    sort_order=3,
                    item_type="material",
                    material_id=paper_material.id,
                    title=paper_material.title,
                )
            )
            db.add_all(items)

        if not await first_or_none(
            db, select(LearningHistory).where(LearningHistory.enrollment_id == enroll.id)
        ):
            db.add_all(
                [
                    LearningHistory(
                        enrollment_id=enroll.id,
                        learner_id=learner_master.id,
                        event_type="start",
                        title="受講開始",
                        detail="ビジネス基礎通信講座を開始",
                    ),
                    LearningHistory(
                        enrollment_id=enroll.id,
                        learner_id=learner_master.id,
                        event_type="view",
                        title="オリエンテーション視聴",
                        detail="進捗 100%",
                    ),
                    LearningHistory(
                        enrollment_id=enroll.id,
                        learner_id=learner_master.id,
                        event_type="submit",
                        title="第1回レポート提出",
                    ),
                ]
            )

        if not await first_or_none(db, select(Grade).where(Grade.enrollment_id == enroll.id)):
            db.add(
                Grade(
                    enrollment_id=enroll.id,
                    learner_id=learner_master.id,
                    source=GradeSource.ASSIGNMENT,
                    title="第1回レポート",
                    score=82,
                    max_score=100,
                    passed=True,
                )
            )

        assignment = await first_or_none(db, select(Assignment).where(Assignment.code == "ASN-PERS-01"))
        if assignment is None:
            assignment = Assignment(
                course_id=personal.id,
                code="ASN-PERS-01",
                title="第1回レポート",
                description="ビジネス文書の書き方を提出してください。",
                due_days=14,
                max_score=100,
                requires_correction=True,
                sort_order=1,
            )
            db.add(assignment)
            await db.flush()

        submission = await first_or_none(
            db, select(AssignmentSubmission).where(AssignmentSubmission.enrollment_id == enroll.id)
        )
        if not await first_or_none(
            db, select(CorrectionResult).where(CorrectionResult.enrollment_id == enroll.id)
        ):
            corrector = await first_or_none(db, select(User).where(User.email == "corrector@example.com"))
            db.add(
                CorrectionResult(
                    assignment_id=assignment.id,
                    submission_id=submission.id if submission else None,
                    enrollment_id=enroll.id,
                    corrector_id=corrector.id if corrector else None,
                    score=82,
                    status="reviewed",
                    feedback="構成は良いです。結論を先に書くとさらに伝わります。",
                    turnaround_hours=48,
                )
            )

        if not await first_or_none(db, select(Payment).where(Payment.payment_no == "PAY-DEMO-001")):
            db.add(
                Payment(
                    payment_no="PAY-DEMO-001",
                    contract_id=contract.id if contract else None,
                    customer_id=customer.id,
                    amount=Decimal("35820"),
                    method="credit_card",
                    status=PaymentStatus.RECEIVED,
                    paid_at=now - timedelta(days=10),
                    note="デモ入金（個人契約）",
                )
            )
        if not await first_or_none(db, select(Payment).where(Payment.payment_no == "PAY-DEMO-CORP-001")):
            db.add(
                Payment(
                    payment_no="PAY-DEMO-CORP-001",
                    contract_id=corp_contract.id if corp_contract else None,
                    customer_id=corp_customer.id,
                    amount=Decimal("120000"),
                    method="invoice",
                    status=PaymentStatus.PENDING,
                    note="法人請求・入金待ち",
                )
            )

        if not await first_or_none(db, select(Certificate).where(Certificate.certificate_no == "CERT-DEMO-001")):
            # 簿記受講があれば修了証サンプル
            qual_enroll = await first_or_none(
                db, select(Enrollment).where(Enrollment.user_id == learner.id, Enrollment.course_id == qual.id)
            )
            if qual_enroll:
                db.add(
                    Certificate(
                        enrollment_id=qual_enroll.id,
                        certificate_no="CERT-DEMO-001",
                        title="簿記3級 修了認定",
                    )
                )

        await db.commit()

        counts = await db.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM customers) AS customers,
                  (SELECT count(*) FROM learners) AS learners,
                  (SELECT count(*) FROM products) AS products,
                  (SELECT count(*) FROM curricula) AS curricula,
                  (SELECT count(*) FROM learning_histories) AS histories,
                  (SELECT count(*) FROM grades) AS grades,
                  (SELECT count(*) FROM assignments) AS assignments,
                  (SELECT count(*) FROM correction_results) AS corrections,
                  (SELECT count(*) FROM payments) AS payments,
                  (SELECT count(*) FROM courses) AS courses,
                  (SELECT count(*) FROM contracts) AS contracts
                """
            )
        )
        row = counts.mappings().one()
        print("Seed upsert completed.")
        print(
            f"customers={row['customers']} learners={row['learners']} products={row['products']} "
            f"curricula={row['curricula']} histories={row['histories']} grades={row['grades']} "
            f"assignments={row['assignments']} corrections={row['corrections']} payments={row['payments']} "
            f"courses={row['courses']} contracts={row['contracts']}"
        )


if __name__ == "__main__":
    asyncio.run(seed())
