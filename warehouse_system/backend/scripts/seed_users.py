import os
import sys
from sqlalchemy.orm import Session

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, Base, SessionLocal
from app.db.models import User, Worker
from app.core.security import get_password_hash
from app.core.config import settings

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
            warehouse_id=settings.WAREHOUSE_ID
        )
        db.add(manager)

    # Create Inbound/Outbound
    inbound = db.query(User).filter(User.username == "inbound").first()
    if not inbound:
        inbound = User(username="inbound", email="inbound@warehouse.local", hashed_password=get_password_hash("inbound123"), role="INBOUND", warehouse_id=settings.WAREHOUSE_ID)
        db.add(inbound)

    outbound = db.query(User).filter(User.username == "outbound").first()
    if not outbound:
        outbound = User(username="outbound", email="outbound@warehouse.local", hashed_password=get_password_hash("outbound123"), role="OUTBOUND", warehouse_id=settings.WAREHOUSE_ID)
        db.add(outbound)
        
    db.commit()
    
    # Create 50 workers
    import random
    skills = ['Beginner', 'Intermediate', 'Expert']
    zones = ['Picking_A', 'Picking_B', 'Packing_A', 'Receiving_A', 'Putaway_A']
    
    for i in range(1, 51):
        username = f"worker{i:03d}"
        worker_id = f"W{i:04d}"
        if not db.query(User).filter(User.username == username).first():
            user = User(
                username=username,
                email=f"{username}@warehouse.local",
                hashed_password=get_password_hash(worker_id),
                role="WORKER",
                warehouse_id=settings.WAREHOUSE_ID
            )
            db.add(user)
            db.flush() # get user.id
            
            worker = Worker(
                user_id=user.id,
                worker_id=worker_id,
                name=f"Worker {i}",
                warehouse_id=settings.WAREHOUSE_ID,
                skill_level=random.choice(skills),
                experience_years=round(random.uniform(0.5, 10.0), 1),
                assigned_zone=random.choice(zones),
                shift=random.choice([1, 2, 3])
            )
            db.add(worker)
            
    db.commit()
    
    # Seed WorkloadQueue
    from app.db.models import WorkloadQueue, Task, OperationalEvent
    if not db.query(WorkloadQueue).first():
        db.add(WorkloadQueue(warehouse_id=settings.WAREHOUSE_ID, process_type="RECEIVING", volume=2500))
        db.add(WorkloadQueue(warehouse_id=settings.WAREHOUSE_ID, process_type="PICKING", volume=8400))
        db.add(WorkloadQueue(warehouse_id=settings.WAREHOUSE_ID, process_type="PACKING", volume=3200))
        
        # Seed some active tasks
        for i in range(12):
            db.add(Task(warehouse_id=settings.WAREHOUSE_ID, process_type="PICKING", zone="PICKING_A",
                        priority="HIGH", status="PENDING",
                        instructions=f"Pick order batch {i}"))
            
        # Seed an event
        db.add(OperationalEvent(warehouse_id=settings.WAREHOUSE_ID, event_type="SHIFT_START", description="Shift 1 started", details={}))

    db.commit()

    # Seed labor standards (units one worker processes per hour, per process)
    from app.db.models import LaborStandard
    standards = {
        "RECEIVING": 120.0, "INSPECTION": 90.0, "PUTAWAY": 80.0,
        "PICKING": 60.0, "PACKING": 70.0, "DISPATCH": 110.0,
    }
    for ptype, uph in standards.items():
        if not db.query(LaborStandard).filter_by(warehouse_id=settings.WAREHOUSE_ID, process_type=ptype).first():
            db.add(LaborStandard(warehouse_id=settings.WAREHOUSE_ID, process_type=ptype, units_per_hour=uph))

    # Mark a pool of workers on-shift so the assignment engine has candidates
    shift_workers = db.query(Worker).filter(Worker.shift == 1, Worker.status != "ON_SHIFT").limit(12).all()
    for w in shift_workers:
        w.status = "ON_SHIFT"

    # Seed 8 weeks of daily volume history (weekly seasonality + gentle noise)
    # so forecasting/backtesting work from a fresh container.
    from app.db.models import VolumeHistory
    from datetime import datetime, timedelta
    if not db.query(VolumeHistory).first():
        base = {"RECEIVING": 2400, "INSPECTION": 2000, "PUTAWAY": 1900,
                "PICKING": 5200, "PACKING": 3400, "DISPATCH": 3000}
        random.seed(42)
        today = datetime.utcnow().date()
        for ptype, avg in base.items():
            for d in range(56):
                day = today - timedelta(days=56 - d)
                weekend_drop = 0.6 if day.weekday() >= 5 else 1.0
                noise = random.uniform(0.9, 1.1)
                db.add(VolumeHistory(
                    warehouse_id=settings.WAREHOUSE_ID, process_type=ptype,
                    date=datetime.combine(day, datetime.min.time()),
                    volume=round(avg * weekend_drop * noise, 1),
                ))

    db.commit()
    db.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_data()
