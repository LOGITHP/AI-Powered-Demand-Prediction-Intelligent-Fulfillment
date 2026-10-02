from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models.all_models import Product
from app.schemas.all_schemas import ProductResponse

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).limit(50)) # limit for UI speed
    return result.scalars().all()

@router.get("/search", response_model=List[ProductResponse])
async def search_products(q: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.name.ilike(f"%{q}%")).limit(20)
    )
    return result.scalars().all()

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
