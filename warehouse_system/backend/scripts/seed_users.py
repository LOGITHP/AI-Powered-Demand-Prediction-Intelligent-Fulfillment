import os
import sys
from sqlalchemy.orm import Session

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, Base, SessionLocal
from app.db.models import User, Worker
from app.core.security import get_password_hash

def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create Manager
    manager = db.query(User).filter(User.username == "manager").first()
    if not manager:
        manager = User(
            username="manager",
            email="manager@warehouse.local",
            hashed_password=get_password_hash("manager123"),
            role="MANAGER",
            warehouse_id="WH01"
        )
        db.add(manager)

    # Create Inbound/Outbound
    inbound = db.query(User).filter(User.username == "inbound").first()
    if not inbound:
        inbound = User(username="inbound", email="inbound@warehouse.local", hashed_password=get_password_hash("inbound123"), role="INBOUND", warehouse_id="WH01")
        db.add(inbound)

    outbound = db.query(User).filter(User.username == "outbound").first()
    if not outbound:
        outbound = User(username="outbound", email="outbound@warehouse.local", hashed_password=get_password_hash("outbound123"), role="OUTBOUND", warehouse_id="WH01")
        db.add(outbound)
        
    db.commit()
    
    # Create 50 workers
    import random
    skills = ['Beginner', 'Intermediate', 'Expert']
    zones = ['Picking_A', 'Picking_B', 'Packing_A', 'Receiving_A', 'Putaway_A']
    
    for i in range(1, 51):
        username = f"worker{i:03d}"
        if not db.query(User).filter(User.username == username).first():
            user = User(
                username=username,
                email=f"{username}@warehouse.local",
                hashed_password=get_password_hash("worker123"),
                role="WORKER",
                warehouse_id="WH01"
            )
            db.add(user)
            db.flush() # get user.id
            
            worker = Worker(
                user_id=user.id,
                worker_id=f"W{i:04d}",
                name=f"Worker {i}",
                warehouse_id="WH01",
                skill_level=random.choice(skills),
                experience_years=round(random.uniform(0.5, 10.0), 1),
                assigned_zone=random.choice(zones),
                shift=random.choice([1, 2, 3])
            )
            db.add(worker)
            
    db.commit()
    db.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_data()
