from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.schemas.all_schemas import LocationRequest, StoreRecommendationResponse
from app.models.all_models import Store, Inventory
from app.services.recommendation_engine import calculate_distance, calculate_fulfillment_score
import random

router = APIRouter()

@router.post("/store", response_model=StoreRecommendationResponse)
async def recommend_store(request: LocationRequest, db: AsyncSession = Depends(get_db)):
    # 1. Find all stores
    result = await db.execute(select(Store).where(Store.is_active == True))
    stores = result.scalars().all()
    
    candidates = []
    
    for store in stores:
        dist = calculate_distance(request.customer_lat, request.customer_lng, store.latitude, store.longitude)
        
        # Only consider stores within 15km for prototype
        if dist > 15:
            continue
            
        # 2. Check inventory
        inv_res = await db.execute(
            select(Inventory).where(
                Inventory.store_id == store.id,
                Inventory.product_id == request.product_id
            )
        )
        inv = inv_res.scalars().first()
        
        reported_qty = inv.reported_quantity if inv else 0
        inventory_adequacy = 1.0 if reported_qty >= request.quantity else (reported_qty / request.quantity if request.quantity > 0 else 0)
        
        # 3. Predict Availability (Simulated with random near accuracy for prototype speed if model not loaded)
        # Ideally, we load the ML model here, but for simplicity in the API response without blocking:
        # We will use the historical inventory accuracy of the store
        acc = inv.inventory_accuracy if inv else 0.8
        availability_confidence = max(0.1, min(0.99, acc + random.uniform(-0.1, 0.1)))
        
        # 4. Predict Future Risk (Simulate)
        future_risk = 0.2 if reported_qty > request.quantity * 2 else 0.8
        
        # 5. SLA
        sla = 1.0 if dist < 5 else (0.5 if dist < 10 else 0.2)
        
        # 6. Score
        score = calculate_fulfillment_score(
            availability_confidence, inventory_adequacy, dist, future_risk, sla
        )
        
        candidates.append({
            "store_id": store.id,
            "name": store.name,
            "distance_km": round(dist, 1),
            "availability_confidence": round(availability_confidence, 2),
            "fulfillment_score": score,
            "inventory_reported": reported_qty
        })
        
    # Sort candidates by score descending
    candidates.sort(key=lambda x: x["fulfillment_score"], reverse=True)
    
    if not candidates:
        return {"recommended_store": {}, "alternatives": []}
        
    recommended = candidates[0]
    alternatives = candidates[1:4] # top 3 alternatives
    
    return {
        "recommended_store": recommended,
        "alternatives": alternatives
    }
