import math
from typing import List, Dict

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Haversine formula
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_fulfillment_score(
    availability_confidence: float,
    inventory_adequacy: float,
    distance_km: float,
    future_risk: float,
    sla_feasibility: float
) -> int:
    """
    Availability Confidence: 40%
    Inventory Adequacy:      20%
    Distance:                20%
    Future Risk (Inverted):  10%
    Delivery/SLA:            10%
    """
    
    # Normalize distance (assuming max reasonable distance is 20km)
    norm_distance = max(0, 100 - (distance_km * 5))
    
    score = (
        (availability_confidence * 100 * 0.40) +
        (inventory_adequacy * 100 * 0.20) +
        (norm_distance * 0.20) +
        ((1.0 - future_risk) * 100 * 0.10) +
        (sla_feasibility * 100 * 0.10)
    )
    
    return min(100, max(0, int(score)))

async def recommend_store_for_product(db, product_id: int, quantity: int, customer_lat: float, customer_lng: float):
    # This would fetch stores, check inventory, run models, and score them
    # Placeholder for prototype logic inside API route
    pass
