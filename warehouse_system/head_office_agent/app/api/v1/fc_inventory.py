from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.core import get_db
from models.core import FCInventory
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class InventoryUpdateReq(BaseModel):
    fc_id: str
    product_id: str
    available_quantity: int
    reserved_quantity: int
    incoming_quantity: int

class InventoryActionReq(BaseModel):
    fc_id: str
    product_id: str
    quantity: int

@router.get("/")
def get_all_inventory(db: Session = Depends(get_db)):
    items = db.query(FCInventory).all()
    return items

@router.get("/{product_id}")
def get_inventory(product_id: str, db: Session = Depends(get_db)):
    items = db.query(FCInventory).filter(FCInventory.product_id == product_id).all()
    return items

@router.post("/update")
def update_inventory(req: InventoryUpdateReq, db: Session = Depends(get_db)):
    item = db.query(FCInventory).filter(
        FCInventory.fc_id == req.fc_id, 
        FCInventory.product_id == req.product_id
    ).first()
    
    if not item:
        item = FCInventory(
            fc_id=req.fc_id,
            product_id=req.product_id,
            available_quantity=req.available_quantity,
            reserved_quantity=req.reserved_quantity,
            incoming_quantity=req.incoming_quantity
        )
        db.add(item)
    else:
        item.available_quantity = req.available_quantity
        item.reserved_quantity = req.reserved_quantity
        item.incoming_quantity = req.incoming_quantity
        
    db.commit()
    db.refresh(item)
    return item

@router.post("/reserve")
def reserve_inventory(req: InventoryActionReq, db: Session = Depends(get_db)):
    item = db.query(FCInventory).filter(
        FCInventory.fc_id == req.fc_id, 
        FCInventory.product_id == req.product_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Product not found in FC")
        
    if item.available_quantity < req.quantity:
        raise HTTPException(status_code=400, detail="Insufficient available quantity")
        
    item.available_quantity -= req.quantity
    item.reserved_quantity += req.quantity
    db.commit()
    db.refresh(item)
    return item

@router.post("/release")
def release_inventory(req: InventoryActionReq, db: Session = Depends(get_db)):
    item = db.query(FCInventory).filter(
        FCInventory.fc_id == req.fc_id, 
        FCInventory.product_id == req.product_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Product not found in FC")
        
    if item.reserved_quantity < req.quantity:
        raise HTTPException(status_code=400, detail="Insufficient reserved quantity")
        
    item.reserved_quantity -= req.quantity
    item.available_quantity += req.quantity
    db.commit()
    db.refresh(item)
    return item
