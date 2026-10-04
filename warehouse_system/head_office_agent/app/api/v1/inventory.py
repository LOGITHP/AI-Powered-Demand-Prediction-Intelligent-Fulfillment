from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.core import get_db
from models.core import InventorySnapshot

router = APIRouter()

@router.get("/")
def get_global_inventory(db: Session = Depends(get_db)):
    inv = db.query(InventorySnapshot).all()
    # Group by product
    products = {}
    for i in inv:
        if i.product_id not in products:
            products[i.product_id] = {"available": 0, "reserved": 0, "locations": {}}
        
        products[i.product_id]["available"] += i.available_quantity
        products[i.product_id]["reserved"] += i.reserved_quantity
        products[i.product_id]["locations"][i.agent_id] = {
            "available": i.available_quantity,
            "reserved": i.reserved_quantity
        }
        
    return products
