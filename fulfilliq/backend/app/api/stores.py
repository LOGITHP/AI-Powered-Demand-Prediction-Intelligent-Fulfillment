from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models.all_models import Store, Inventory, Product
from app.schemas.all_schemas import StoreResponse, InventoryResponse

router = APIRouter()

@router.get("/", response_model=List[StoreResponse])
async def get_stores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store))
    return result.scalars().all()

@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalars().first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

@router.get("/{store_id}/inventory")
async def get_store_inventory(store_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.store_id == store_id)
    )
    items = result.all()
    
    return [
        {
            "inventory_id": inv.id,
            "product_id": prod.id,
            "sku": prod.sku,
            "name": prod.name,
            "reported_quantity": inv.reported_quantity,
            "reserved_quantity": inv.reserved_quantity,
            "inventory_accuracy": inv.inventory_accuracy
        }
        for inv, prod in items
    ]
