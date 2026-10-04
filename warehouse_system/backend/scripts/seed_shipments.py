from app.core.config import settings
import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, Base, SessionLocal
from app.db.models import (
    Product, StorageLocation, InboundShipment, InboundShipmentItem,
    OutboundOrder, OutboundOrderItem, InventoryRecord, Task, Notification
)

def seed_real_data():
    db = SessionLocal()
    
    WAREHOUSE_ID = settings.WAREHOUSE_ID
    
    # 1. Products
    products = [
        {"sku": "LAPTOP-01", "name": "ThinkPad T14", "category": "Electronics"},
        {"sku": "MONITOR-01", "name": "Dell 27-inch 4K", "category": "Electronics"},
        {"sku": "CHAIR-01", "name": "Ergonomic Office Chair", "category": "Furniture"},
        {"sku": "DESK-01", "name": "Standing Desk", "category": "Furniture"},
        {"sku": "CABLE-01", "name": "HDMI Cable 2m", "category": "Accessories"},
        {"sku": "KEYBOARD-01", "name": "Mechanical Keyboard", "category": "Accessories"},
        {"sku": "MOUSE-01", "name": "Wireless Mouse", "category": "Accessories"},
    ]
    
    db_products = []
    for p in products:
        prod = db.query(Product).filter(Product.sku == p["sku"], Product.warehouse_id == WAREHOUSE_ID).first()
        if not prod:
            prod = Product(sku=p["sku"], name=p["name"], category=p["category"], warehouse_id=WAREHOUSE_ID)
            db.add(prod)
        db_products.append(prod)
    
    db.commit()
    db_products = db.query(Product).filter(Product.warehouse_id == WAREHOUSE_ID).all()
    
    # 2. Locations
    zones = ["RECEIVING", "INSPECTION", "PUTAWAY", "PICKING", "PACKING", "LOADING"]
    for z in zones:
        for a in range(1, 4):
            loc = db.query(StorageLocation).filter(StorageLocation.zone == z, StorageLocation.aisle == f"A{a}").first()
            if not loc:
                loc = StorageLocation(warehouse_id=WAREHOUSE_ID, zone=z, aisle=f"A{a}", rack="R1", bin="B1", capacity=1000, current_occupancy=0)
                db.add(loc)
    
    db.commit()
    locations = db.query(StorageLocation).filter(StorageLocation.warehouse_id == WAREHOUSE_ID).all()
    
    # 3. Inventory Records
    for p in db_products:
        inv = db.query(InventoryRecord).filter(InventoryRecord.product_id == p.id).first()
        if not inv:
            inv = InventoryRecord(warehouse_id=WAREHOUSE_ID, product_id=p.id, location_id=locations[-1].id, quantity=random.randint(50, 500), reserved_quantity=0)
            db.add(inv)
            
    db.commit()
    
    # 4. Inbound Shipments
    suppliers = ["TechCorp", "FurnitureHub", "AccessoryWorld"]
    for i in range(5):
        sid = f"SHP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        status = random.choice(["EXPECTED", "ARRIVED", "RECEIVING", "INSPECTION", "PUTAWAY", "COMPLETED"])
        
        expected_arrival = datetime.utcnow() + timedelta(hours=random.randint(-48, 48))
        actual_arrival = expected_arrival + timedelta(hours=random.uniform(-2, 5)) if status != "EXPECTED" else None
        
        s = InboundShipment(
            shipment_id=sid,
            warehouse_id=WAREHOUSE_ID,
            supplier=random.choice(suppliers),
            vehicle_number=f"TRK-{random.randint(1000, 9999)}",
            driver_name=f"Driver {i}",
            expected_arrival=expected_arrival,
            actual_arrival=actual_arrival,
            priority=random.choice(["NORMAL", "HIGH", "URGENT"]),
            status=status,
            total_items=0
        )
        db.add(s)
        db.flush()
        
        total_items = 0
        for _ in range(random.randint(1, 4)):
            prod = random.choice(db_products)
            qty = random.randint(10, 100)
            item = InboundShipmentItem(
                shipment_id=sid,
                product_id=prod.id,
                expected_quantity=qty,
                received_quantity=qty if status in ["INSPECTION", "PUTAWAY", "COMPLETED"] else 0,
                accepted_quantity=qty if status in ["PUTAWAY", "COMPLETED"] else 0
            )
            db.add(item)
            total_items += qty
            
        s.total_items = total_items
        
    # 5. Outbound Orders (Delivery Partners)
    customers = ["FedEx", "UPS", "DHL", "LocalCourier", "Amazon Logistics"]
    for i in range(5):
        oid = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        status = random.choice(["CREATED", "RELEASED", "PICKING", "PACKING", "LOADING", "COMPLETED"])
        
        req_time = datetime.utcnow() + timedelta(hours=random.randint(-24, 48))
        
        o = OutboundOrder(
            order_id=oid,
            warehouse_id=WAREHOUSE_ID,
            customer=random.choice(customers), # Delivery partner
            priority=random.choice(["NORMAL", "HIGH", "URGENT"]),
            required_dispatch_time=req_time,
            status=status,
            total_items=0
        )
        db.add(o)
        db.flush()
        
        total_items = 0
        for _ in range(random.randint(1, 4)):
            prod = random.choice(db_products)
            qty = random.randint(5, 20)
            item = OutboundOrderItem(
                order_id=oid,
                product_id=prod.id,
                required_quantity=qty,
                picked_quantity=qty if status in ["PACKING", "LOADING", "COMPLETED"] else 0,
                packed_quantity=qty if status in ["LOADING", "COMPLETED"] else 0,
                loaded_quantity=qty if status == "COMPLETED" else 0
            )
            db.add(item)
            total_items += qty
            
        o.total_items = total_items

    db.commit()
    db.close()
    print("Shipments and Orders seeded successfully!")

if __name__ == "__main__":
    seed_real_data()
