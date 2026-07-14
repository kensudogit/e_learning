"""受講履歴（LearningHistory）書き込みヘルパー."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core_entities import LearningHistory


async def record_learning_event(
    db: AsyncSession,
    *,
    enrollment_id: UUID,
    event_type: str,
    title: str,
    detail: str | None = None,
    payload: dict[str, Any] | None = None,
    learner_id: UUID | None = None,
) -> LearningHistory:
    event = LearningHistory(
        enrollment_id=enrollment_id,
        learner_id=learner_id,
        event_type=event_type,
        title=title,
        detail=detail,
        payload=payload,
    )
    db.add(event)
    return event
