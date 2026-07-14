"""通信教育・教材発送 API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.domain import Material, User, UserRole
from app.models.platform import (
    BundleProduct,
    InventoryItem,
    MaterialEdition,
    ShippingAddress,
    ShippingOrder,
    ShippingStatus,
    StockMovement,
    StockMoveType,
)
from app.schemas.platform import (
    AddressCreate,
    AddressRead,
    BundleCreate,
    BundleRead,
    EditionCreate,
    EditionRead,
    InventoryAdjust,
    InventoryRead,
    ShippingAction,
    ShippingCreate,
    ShippingRead,
)

router = APIRouter(tags=["shipping"])


@router.post("/shipping/addresses", response_model=AddressRead, status_code=201)
async def create_address(
    payload: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShippingAddress:
    if payload.is_default:
        existing = (
            await db.execute(
                select(ShippingAddress).where(
                    ShippingAddress.user_id == current_user.id, ShippingAddress.is_default.is_(True)
                )
            )
        ).scalars().all()
        for a in existing:
            a.is_default = False
    addr = ShippingAddress(user_id=current_user.id, **payload.model_dump())
    db.add(addr)
    await db.flush()
    await db.refresh(addr)
    return addr


@router.get("/shipping/addresses", response_model=list[AddressRead])
async def list_addresses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ShippingAddress]:
    result = await db.execute(select(ShippingAddress).where(ShippingAddress.user_id == current_user.id))
    return list(result.scalars().all())


@router.patch("/shipping/addresses/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: str,
    payload: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShippingAddress:
    """住所変更."""
    addr = (
        await db.execute(
            select(ShippingAddress).where(
                ShippingAddress.id == address_id, ShippingAddress.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    if addr is None:
        raise HTTPException(status_code=404, detail="住所が見つかりません")
    for k, v in payload.model_dump().items():
        setattr(addr, k, v)
    await db.flush()
    await db.refresh(addr)
    return addr


@router.post("/shipping/editions", response_model=EditionRead, status_code=201)
async def create_edition(
    payload: EditionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaterialEdition:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="版管理権限がありません")
    mat = (await db.execute(select(Material).where(Material.id == payload.material_id))).scalar_one_or_none()
    if mat is None:
        raise HTTPException(status_code=404, detail="教材が見つかりません")
    if payload.is_current:
        olds = (
            await db.execute(
                select(MaterialEdition).where(
                    MaterialEdition.material_id == payload.material_id, MaterialEdition.is_current.is_(True)
                )
            )
        ).scalars().all()
        for o in olds:
            o.is_current = False
    edition = MaterialEdition(**payload.model_dump())
    db.add(edition)
    await db.flush()
    await db.refresh(edition)
    return edition


@router.get("/shipping/editions", response_model=list[EditionRead])
async def list_editions(
    material_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MaterialEdition]:
    stmt = select(MaterialEdition).order_by(MaterialEdition.revised_at.desc())
    if material_id:
        stmt = stmt.where(MaterialEdition.material_id == material_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/shipping/inventory/adjust", response_model=InventoryRead)
async def adjust_inventory(
    payload: InventoryAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryItem:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="在庫管理権限がありません")
    inv = (
        await db.execute(
            select(InventoryItem).where(
                InventoryItem.material_id == payload.material_id,
                InventoryItem.warehouse == payload.warehouse,
            )
        )
    ).scalar_one_or_none()
    if inv is None:
        inv = InventoryItem(
            material_id=payload.material_id,
            edition_id=payload.edition_id,
            warehouse=payload.warehouse,
            quantity=0,
        )
        db.add(inv)
        await db.flush()
    inv.quantity = max(0, inv.quantity + payload.quantity_delta)
    if payload.edition_id:
        inv.edition_id = payload.edition_id
    db.add(
        StockMovement(
            inventory_id=inv.id,
            move_type=payload.move_type,
            quantity=payload.quantity_delta,
            note=payload.note,
        )
    )
    # materials.stock_quantity も同期
    mat = (await db.execute(select(Material).where(Material.id == payload.material_id))).scalar_one_or_none()
    if mat is not None:
        mat.stock_quantity = inv.quantity
    await db.flush()
    await db.refresh(inv)
    return inv


@router.get("/shipping/inventory", response_model=list[InventoryRead])
async def list_inventory(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[InventoryItem]:
    return list((await db.execute(select(InventoryItem))).scalars().all())


@router.post("/shipping/orders", response_model=ShippingRead, status_code=201)
async def create_shipping_order(
    payload: ShippingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShippingOrder:
    """発送時期指定・分割発送・海外発送."""
    addr = (await db.execute(select(ShippingAddress).where(ShippingAddress.id == payload.address_id))).scalar_one_or_none()
    if addr is None:
        raise HTTPException(status_code=404, detail="住所が見つかりません")
    data = payload.model_dump()
    data["is_overseas"] = payload.is_overseas or (addr.country != "JP")
    order = ShippingOrder(**data, status=ShippingStatus.SCHEDULED)
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order


@router.get("/shipping/orders", response_model=list[ShippingRead])
async def list_shipping_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ShippingOrder]:
    if current_user.role in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        result = await db.execute(select(ShippingOrder).order_by(ShippingOrder.created_at.desc()))
    else:
        addrs = (
            await db.execute(select(ShippingAddress.id).where(ShippingAddress.user_id == current_user.id))
        ).scalars().all()
        result = await db.execute(
            select(ShippingOrder)
            .where(ShippingOrder.address_id.in_(list(addrs) or [None]))
            .order_by(ShippingOrder.created_at.desc())
        )
    return list(result.scalars().all())


@router.post("/shipping/orders/{order_id}/ship", response_model=ShippingRead)
async def mark_shipped(
    order_id: str,
    payload: ShippingAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShippingOrder:
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="発送処理権限がありません")
    order = (await db.execute(select(ShippingOrder).where(ShippingOrder.id == order_id))).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="発送指示が見つかりません")
    order.status = ShippingStatus.SHIPPED
    order.shipped_at = datetime.now(UTC)
    order.tracking_no = payload.tracking_no
    # 在庫減
    inv = (
        await db.execute(select(InventoryItem).where(InventoryItem.material_id == order.material_id))
    ).scalar_one_or_none()
    if inv and inv.quantity > 0:
        inv.quantity -= 1
        db.add(StockMovement(inventory_id=inv.id, move_type=StockMoveType.OUT, quantity=-1, note="ship"))
    await db.flush()
    await db.refresh(order)
    return order


@router.post("/shipping/orders/{order_id}/reship", response_model=ShippingRead, status_code=201)
async def reship(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShippingOrder:
    """再発送."""
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="再発送権限がありません")
    parent = (await db.execute(select(ShippingOrder).where(ShippingOrder.id == order_id))).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=404, detail="元発送が見つかりません")
    child = ShippingOrder(
        enrollment_id=parent.enrollment_id,
        contract_id=parent.contract_id,
        address_id=parent.address_id,
        material_id=parent.material_id,
        edition_id=parent.edition_id,
        status=ShippingStatus.RESHIPPED,
        scheduled_ship_date=parent.scheduled_ship_date,
        split_group=parent.split_group,
        split_sequence=parent.split_sequence,
        is_overseas=parent.is_overseas,
        parent_order_id=parent.id,
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return child


@router.post("/shipping/orders/{order_id}/return", response_model=ShippingRead)
async def return_shipment(
    order_id: str,
    payload: ShippingAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShippingOrder:
    """返送."""
    order = (await db.execute(select(ShippingOrder).where(ShippingOrder.id == order_id))).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="発送指示が見つかりません")
    order.status = ShippingStatus.RETURNED
    order.return_reason = payload.return_reason
    inv = (
        await db.execute(select(InventoryItem).where(InventoryItem.material_id == order.material_id))
    ).scalar_one_or_none()
    if inv:
        inv.quantity += 1
        db.add(StockMovement(inventory_id=inv.id, move_type=StockMoveType.RETURN, quantity=1, note="return"))
    await db.flush()
    await db.refresh(order)
    return order


@router.post("/shipping/bundles", response_model=BundleRead, status_code=201)
async def create_bundle(
    payload: BundleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BundleProduct:
    """eラーニングとのセット商品."""
    if current_user.role not in {UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise HTTPException(status_code=403, detail="セット商品作成権限がありません")
    bundle = BundleProduct(**payload.model_dump())
    db.add(bundle)
    await db.flush()
    await db.refresh(bundle)
    return bundle


@router.get("/shipping/bundles", response_model=list[BundleRead])
async def list_bundles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[BundleProduct]:
    result = await db.execute(select(BundleProduct).where(BundleProduct.is_active.is_(True)))
    return list(result.scalars().all())
