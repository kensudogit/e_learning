"""主要テーブルの件数・サンプル一覧 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.core_entities import (
    Assignment,
    CorrectionResult,
    Curriculum,
    Customer,
    Grade,
    Learner,
    LearningHistory,
    Payment,
    Product,
)
from app.models.domain import (
    Application,
    AssignmentSubmission,
    Certificate,
    Course,
    Enrollment,
    Inquiry,
    Lesson,
    Material,
)
from app.models.platform import (
    BillingDocument,
    Contract,
    LearningProgress,
    Organization,
    ShippingOrder,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

# 日本語ラベル ↔ 物理テーブル
TABLE_DEFS: list[dict[str, Any]] = [
    {"key": "customers", "label": "顧客", "model": Customer, "title_cols": ("customer_no", "name")},
    {"key": "learners", "label": "受講者", "model": Learner, "title_cols": ("learner_no", "full_name")},
    {"key": "organizations", "label": "法人", "model": Organization, "title_cols": ("code", "name")},
    {"key": "contracts", "label": "契約", "model": Contract, "title_cols": ("contract_no", "status")},
    {"key": "applications", "label": "申込", "model": Application, "title_cols": ("full_name", "status")},
    {"key": "products", "label": "商品", "model": Product, "title_cols": ("product_code", "name")},
    {"key": "courses", "label": "講座", "model": Course, "title_cols": ("code", "title")},
    {"key": "curricula", "label": "カリキュラム", "model": Curriculum, "title_cols": ("code", "title")},
    {"key": "materials", "label": "教材", "model": Material, "title_cols": ("title", "material_type")},
    {
        "key": "learning_histories",
        "label": "受講履歴",
        "model": LearningHistory,
        "title_cols": ("event_type", "title"),
    },
    {
        "key": "learning_progress",
        "label": "進捗",
        "model": LearningProgress,
        "title_cols": ("progress_percent", "completed"),
    },
    {"key": "grades", "label": "成績", "model": Grade, "title_cols": ("title", "score")},
    {"key": "assignments", "label": "課題", "model": Assignment, "title_cols": ("code", "title")},
    {
        "key": "correction_results",
        "label": "添削結果",
        "model": CorrectionResult,
        "title_cols": ("status", "score"),
    },
    {
        "key": "billing_documents",
        "label": "請求",
        "model": BillingDocument,
        "title_cols": ("document_no", "doc_type"),
    },
    {"key": "payments", "label": "入金", "model": Payment, "title_cols": ("payment_no", "amount")},
    {
        "key": "shipping_orders",
        "label": "発送",
        "model": ShippingOrder,
        "title_cols": ("status", "tracking_no"),
    },
    {"key": "inquiries", "label": "問い合わせ", "model": Inquiry, "title_cols": ("subject", "status")},
    {
        "key": "certificates",
        "label": "修了・資格",
        "model": Certificate,
        "title_cols": ("certificate_no", "title"),
    },
]


def _row_summary(obj: Any, title_cols: tuple[str, ...]) -> dict[str, Any]:
    parts = []
    for col in title_cols:
        val = getattr(obj, col, None)
        if val is None:
            continue
        if hasattr(val, "value"):
            val = val.value
        parts.append(str(val))
    return {
        "id": str(getattr(obj, "id", "")),
        "summary": " · ".join(parts) if parts else str(getattr(obj, "id", "")),
    }


@router.get("/tables")
async def list_core_tables(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """主要テーブルの件数とサンプル行."""
    tables: list[dict[str, Any]] = []
    for spec in TABLE_DEFS:
        model = spec["model"]
        count = (await db.execute(select(func.count()).select_from(model))).scalar_one()
        rows = (await db.execute(select(model).limit(5))).scalars().all()
        tables.append(
            {
                "key": spec["key"],
                "label": spec["label"],
                "table": model.__tablename__,
                "count": int(count),
                "samples": [_row_summary(r, spec["title_cols"]) for r in rows],
            }
        )

    # 補足: レッスン数（カリキュラム構成要素）
    lesson_count = (await db.execute(select(func.count()).select_from(Lesson))).scalar_one()
    submission_count = (
        await db.execute(select(func.count()).select_from(AssignmentSubmission))
    ).scalar_one()
    enrollment_count = (await db.execute(select(func.count()).select_from(Enrollment))).scalar_one()

    return {
        "tables": tables,
        "extras": {
            "lessons": int(lesson_count),
            "assignment_submissions": int(submission_count),
            "enrollments": int(enrollment_count),
        },
    }


@router.get("/tables/{key}")
async def get_table_rows(key: str, limit: int = 50, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    spec = next((t for t in TABLE_DEFS if t["key"] == key), None)
    if spec is None:
        return {"key": key, "label": key, "rows": [], "count": 0, "error": "unknown table"}
    model = spec["model"]
    count = (await db.execute(select(func.count()).select_from(model))).scalar_one()
    rows = (await db.execute(select(model).limit(min(limit, 200)))).scalars().all()
    serialized = []
    for r in rows:
        item: dict[str, Any] = {"id": str(r.id)}
        for col in r.__table__.columns.keys():
            if col == "id":
                continue
            val = getattr(r, col)
            if hasattr(val, "value"):
                val = val.value
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            elif isinstance(val, (int, float, str, bool)) or val is None:
                pass
            else:
                val = str(val)
            item[col] = val
        serialized.append(item)
    return {
        "key": spec["key"],
        "label": spec["label"],
        "table": model.__tablename__,
        "count": int(count),
        "rows": serialized,
    }


@router.get("/mapping")
async def table_mapping() -> list[dict[str, str]]:
    """日本語エンティティ ↔ 物理テーブル対応表."""
    return [
        {"entity": "顧客", "table": "customers"},
        {"entity": "受講者", "table": "learners"},
        {"entity": "法人", "table": "organizations"},
        {"entity": "契約", "table": "contracts"},
        {"entity": "申込", "table": "applications"},
        {"entity": "商品", "table": "products"},
        {"entity": "講座", "table": "courses"},
        {"entity": "カリキュラム", "table": "curricula"},
        {"entity": "教材", "table": "materials"},
        {"entity": "受講履歴", "table": "learning_histories"},
        {"entity": "進捗", "table": "learning_progress"},
        {"entity": "成績", "table": "grades"},
        {"entity": "課題", "table": "assignments"},
        {"entity": "添削結果", "table": "correction_results"},
        {"entity": "請求", "table": "billing_documents"},
        {"entity": "入金", "table": "payments"},
        {"entity": "発送", "table": "shipping_orders"},
        {"entity": "問い合わせ", "table": "inquiries"},
        {"entity": "修了・資格", "table": "certificates"},
    ]
