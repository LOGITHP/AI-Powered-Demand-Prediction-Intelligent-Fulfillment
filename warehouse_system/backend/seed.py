import os
import sys
import uuid
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine, Base
from app.db.models import (
    User, Worker, Warehouse, Product, StorageLocation, InventoryRecord,
    InboundShipment, InboundShipmentItem, OutboundOrder, OutboundOrderItem
)
from app.core.security import get_password_hash
from app.core.config import settings

def seed_database():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Warehouse
        wh = db.query(Warehouse).filter_by(id=settings.WAREHOUSE_ID).first()
        if not wh:
            wh = Warehouse(id=settings.WAREHOUSE_ID, capacity="10000", efficiency_multiplier=1.0)
            db.add(wh)
            db.commit()

        # 2. Users & Workers
        users = [
            {"username": "admin", "email": "admin@wh.com", "role": "ADMIN", "pw": "admin"},
            {"username": "manager", "email": "manager@wh.com", "role": "MANAGER", "pw": "manager"},
            {"username": "inbound_op", "email": "inbound@wh.com", "role": "INBOUND", "pw": "inbound"},
            {"username": "outbound_op", "email": "outbound@wh.com", "role": "OUTBOUND", "pw": "outbound"}
        ]
        
        for u_data in users:
            u = db.query(User).filter_by(username=u_data["username"]).first()
            if not u:
                u = User(
                    username=u_data["username"],
                    email=u_data["email"],
                    hashed_password=get_password_hash(u_data["pw"]),
                    role=u_data["role"],
                    warehouse_id=settings.WAREHOUSE_ID
                )
                db.add(u)
        db.commit()

        worker = db.query(Worker).filter_by(worker_id="W-101").first()
        if not worker:
            w_user = User(
                username="worker1",
                email="worker1@wh.com",
                hashed_password=get_password_hash("worker"),
                role="WORKER",
                warehouse_id=settings.WAREHOUSE_ID
            )
            db.add(w_user)
            db.commit()
            
            worker = Worker(
                user_id=w_user.id,
                worker_id="W-101",
                name="John Doe",
                warehouse_id=settings.WAREHOUSE_ID,
                skill_level="Expert",
                experience_years=3.5,
                assigned_zone="RECEIVING",
                shift=1,
                status="ON_SHIFT"
            )
            db.add(worker)
            db.commit()

        # 3. Products
        p1 = db.query(Product).filter_by(sku="SKU-1001").first()
        if not p1:
            p1 = Product(sku="SKU-1001", name="Premium Widget", category="Electronics", unit_weight=1.5, warehouse_id=settings.WAREHOUSE_ID)
            db.add(p1)
        
        p2 = db.query(Product).filter_by(sku="SKU-1002").first()
        if not p2:
            p2 = Product(sku="SKU-1002", name="Standard Gadget", category="Electronics", unit_weight=0.8, warehouse_id=settings.WAREHOUSE_ID)
            db.add(p2)
        db.commit()

        # 4. Storage Locations
        loc1 = db.query(StorageLocation).filter_by(warehouse_id=settings.WAREHOUSE_ID, zone="A", aisle="1", rack="1", bin="1").first()
        if not loc1:
            loc1 = StorageLocation(warehouse_id=settings.WAREHOUSE_ID, zone="A", aisle="1", rack="1", bin="1", capacity=100)
            db.add(loc1)
        
        loc2 = db.query(StorageLocation).filter_by(warehouse_id=settings.WAREHOUSE_ID, zone="A", aisle="1", rack="1", bin="2").first()
        if not loc2:
            loc2 = StorageLocation(warehouse_id=settings.WAREHOUSE_ID, zone="A", aisle="1", rack="1", bin="2", capacity=100)
            db.add(loc2)
        db.commit()

        # 5. Inventory
        inv = db.query(InventoryRecord).filter_by(warehouse_id=settings.WAREHOUSE_ID, product_id=p1.id).first()
        if not inv:
            inv = InventoryRecord(warehouse_id=settings.WAREHOUSE_ID, product_id=p1.id, location_id=loc1.id, quantity=50, reserved_quantity=0)
            db.add(inv)
            loc1.current_occupancy = 50
            db.commit()

        # 6. Sample Inbound Shipment
        s1 = db.query(InboundShipment).filter_by(warehouse_id=settings.WAREHOUSE_ID).first()
        if not s1:
            sid = f"SHP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-TEST"
            s1 = InboundShipment(
                shipment_id=sid,
                warehouse_id=settings.WAREHOUSE_ID,
                supplier="TechCorp",
                expected_arrival=datetime.utcnow() + timedelta(hours=2),
                status="EXPECTED",
                total_items=100
            )
            db.add(s1)
            db.commit()
            
            s1_item = InboundShipmentItem(
                shipment_id=sid,
                product_id=p2.id,
                expected_quantity=100
            )
            db.add(s1_item)
            db.commit()

        # 7. Sample Outbound Order
        o1 = db.query(OutboundOrder).filter_by(warehouse_id=settings.WAREHOUSE_ID).first()
        if not o1:
            oid = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-TEST"
            o1 = OutboundOrder(
                order_id=oid,
                warehouse_id=settings.WAREHOUSE_ID,
                customer="RetailStore A",
                required_dispatch_time=datetime.utcnow() + timedelta(hours=4),
                status="CREATED",
                total_items=10
            )
            db.add(o1)
            db.commit()
            
            o1_item = OutboundOrderItem(
                order_id=oid,
                product_id=p1.id,
                required_quantity=10
            )
            db.add(o1_item)
            db.commit()

        print("Database seeded successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
