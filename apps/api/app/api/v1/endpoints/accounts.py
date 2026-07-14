"""受講者・アカウント管理 API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import Enrollment, User, UserRole
from app.models.platform import (
    AccountLifecycle,
    AccountMerge,
    AccountStatus,
    FamilyLink,
    LoginIdHistory,
    OrgMemberRole,
    Organization,
    OrganizationMembership,
)
from app.schemas.platform import (
    AccountMergeCreate,
    AccountStatusUpdate,
    FamilyLinkCreate,
    FamilyLinkRead,
    LoginIdChange,
    MembershipCreate,
    MembershipRead,
    OrganizationCreate,
    OrganizationRead,
    UserAccountRead,
)

router = APIRouter(tags=["accounts"])


@router.post("/organizations", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_org(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    if current_user.role not in {UserRole.ADMIN, UserRole.CORPORATE_MANAGER}:
        raise HTTPException(status_code=403, detail="組織作成権限がありません")
    if (await db.execute(select(Organization).where(Organization.code == payload.code))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="組織コードが重複しています")
    org = Organization(**payload.model_dump())
    db.add(org)
    await db.flush()
    db.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=current_user.id,
            role=OrgMemberRole.ORG_ADMIN,
            is_primary=True,
        )
    )
    await db.flush()
    await db.refresh(org)
    return org


@router.get("/organizations", response_model=list[OrganizationRead])
async def list_orgs(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[Organization]:
    result = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
    return list(result.scalars().all())


@router.post("/organizations/{org_id}/members", response_model=MembershipRead, status_code=201)
async def add_member(
    org_id: str,
    payload: MembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationMembership:
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="組織が見つかりません")
    user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    m = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=payload.role,
        is_primary=payload.is_primary,
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)
    return m


@router.get("/organizations/{org_id}/members", response_model=list[MembershipRead])
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[OrganizationMembership]:
    result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.organization_id == org_id)
    )
    return list(result.scalars().all())


@router.get("/accounts/me", response_model=UserAccountRead)
async def my_account(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/accounts/me/memberships", response_model=list[MembershipRead])
async def my_memberships(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationMembership]:
    """複数企業所属の確認."""
    result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("/accounts/family", response_model=FamilyLinkRead, status_code=201)
async def link_family(
    payload: FamilyLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyLink:
    member = (await db.execute(select(User).where(User.id == payload.member_user_id))).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="家族メンバーが見つかりません")
    link = FamilyLink(
        guardian_user_id=current_user.id,
        member_user_id=member.id,
        relation=payload.relation,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


@router.get("/accounts/family", response_model=list[FamilyLinkRead])
async def list_family(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FamilyLink]:
    result = await db.execute(select(FamilyLink).where(FamilyLink.guardian_user_id == current_user.id))
    return list(result.scalars().all())


@router.post("/accounts/merge", status_code=200)
async def merge_accounts(
    payload: AccountMergeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """重複会員の統合（受講・契約を primary に寄せる）."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="統合は管理者のみ")
    if payload.primary_user_id == payload.merged_user_id:
        raise HTTPException(status_code=400, detail="同一ユーザーは統合できません")
    primary = (await db.execute(select(User).where(User.id == payload.primary_user_id))).scalar_one_or_none()
    merged = (await db.execute(select(User).where(User.id == payload.merged_user_id))).scalar_one_or_none()
    if primary is None or merged is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    await db.execute(
        update(Enrollment).where(Enrollment.user_id == merged.id).values(user_id=primary.id)
    )
    merged.is_active = False
    merged.account_status = AccountStatus.WITHDRAWN.value
    db.add(
        AccountMerge(
            primary_user_id=primary.id,
            merged_user_id=merged.id,
            reason=payload.reason,
            performed_by=current_user.id,
        )
    )
    await db.flush()
    return {"status": "merged", "primary_user_id": str(primary.id), "merged_user_id": str(merged.id)}


@router.post("/accounts/me/login-id", response_model=UserAccountRead)
async def change_login_id(
    payload: LoginIdChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    exists = await db.execute(select(User).where(User.login_id == payload.new_login_id))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="既に使用中のログインIDです")
    old = current_user.login_id or current_user.email
    db.add(
        LoginIdHistory(user_id=current_user.id, old_login_id=old, new_login_id=payload.new_login_id)
    )
    current_user.login_id = payload.new_login_id
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/accounts/{user_id}/status", response_model=UserAccountRead)
async def update_account_status(
    user_id: str,
    payload: AccountStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """退会・利用停止."""
    if current_user.role != UserRole.ADMIN and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="権限がありません")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    user.account_status = payload.status.value
    if payload.status in {AccountStatus.SUSPENDED, AccountStatus.WITHDRAWN, AccountStatus.PII_DELETED}:
        user.is_active = False
    db.add(
        AccountLifecycle(user_id=user.id, status=payload.status, reason=payload.reason)
    )
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/accounts/{user_id}/delete-pii", response_model=UserAccountRead)
async def delete_pii(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """個人情報削除（匿名化）."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="管理者のみ実行可能")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    anon = f"deleted-{str(user.id)[:8]}@invalid.local"
    user.email = anon
    user.full_name = "削除済みユーザー"
    user.phone = None
    user.login_id = None
    user.organization_name = None
    user.hashed_password = None
    user.is_active = False
    user.account_status = AccountStatus.PII_DELETED.value
    db.add(
        AccountLifecycle(
            user_id=user.id,
            status=AccountStatus.PII_DELETED,
            reason="pii_deletion",
            pii_deleted_at=datetime.now(UTC),
        )
    )
    await db.flush()
    await db.refresh(user)
    return user
