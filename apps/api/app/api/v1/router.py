from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounts,
    analytics,
    assignments,
    auth,
    contents,
    contracts,
    courses,
    enrollments,
    exams,
    learning,
    shipping,
    support,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(enrollments.router)
api_router.include_router(assignments.router)
api_router.include_router(contents.router)
api_router.include_router(exams.router)
api_router.include_router(support.router)
api_router.include_router(analytics.router)
api_router.include_router(contracts.router)
api_router.include_router(accounts.router)
api_router.include_router(learning.router)
api_router.include_router(shipping.router)
