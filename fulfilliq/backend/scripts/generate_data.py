import asyncio
import sys
import os
from datetime import datetime, timedelta
import random
import uuid

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.all_models import Store, Product, Inventory, HistoricalOrder, User, RoleEnum, StoreTypeEnum
from app.core.security import get_password_hash

AREAS = ["Gandhipuram", "RS Puram", "Peelamedu", "Saibaba Colony", "Singanallur", 
         "Ramanathapuram", "Ukkadam", "Kuniyamuthur", "Saravanampatti", "Kalapatti", 
         "Ganapathy", "Vadavalli", "Sundarapuram", "Podanur", "Town Hall"]
CATEGORIES = ["Grocery", "Beverages", "Personal Care", "Household", "Electronics", 
              "Stationery", "Snacks", "Fruits", "Vegetables", "Baby Care"]

# Coimbatore approx center: 11.0168, 76.9558
CENTER_LAT = 11.0168
CENTER_LNG = 76.9558

async def generate_stores(session, n=50):
    print("Generating stores...")
    stores = []
    for i in range(1, n + 1):
        lat = CENTER_LAT + random.uniform(-0.1, 0.1)
        lng = CENTER_LNG + random.uniform(-0.1, 0.1)
        store = Store(
            name=f"FulfillIQ Store {i:03d}",
            type=random.choice(list(StoreTypeEnum)),
            latitude=lat,
            longitude=lng,
            area=random.choice(AREAS),
            address=f"Demo Address {i}, Coimbatore",
            operating_hours="08:00 AM - 10:00 PM",
            capacity=random.randint(1000, 5000),
            is_active=True
        )
        session.add(store)
        stores.append(store)
    await session.flush()
    return stores

async def generate_products(session, n=500):
    print("Generating products...")
    products = []
    for i in range(1, n + 1):
        cat = random.choice(CATEGORIES)
        prod = Product(
            sku=f"SKU{i:06d}",
            name=f"{cat} Item {i}",
            category=cat,
            price=round(random.uniform(10.0, 500.0), 2),
            unit="piece",
            is_active=True
        )
        session.add(prod)
        products.append(prod)
    await session.flush()
    return products

async def generate_inventory(session, stores, products):
    print("Generating inventory...")
    # Not all stores carry all products. Each store gets random ~100 products.
    for store in stores:
        store_products = random.sample(products, k=min(100, len(products)))
        for prod in store_products:
            inv = Inventory(
                store_id=store.id,
                product_id=prod.id,
                reported_quantity=random.randint(5, 100),
                reorder_level=10,
                safety_stock=5,
                inventory_accuracy=random.uniform(0.7, 1.0)
            )
            session.add(inv)
    await session.flush()

async def generate_orders(session, stores, products, num_orders=30000, days=90):
    print(f"Generating {num_orders} historical orders over {days} days...")
    start_time = datetime.utcnow() - timedelta(days=days)
    
    batch_size = 5000
    batch = []
    
    for i in range(num_orders):
        store = random.choice(stores)
        product = random.choice(products)
        qty = random.randint(1, 5)
        
        # random time
        order_time = start_time + timedelta(minutes=random.randint(0, days * 24 * 60))
        is_weekend = order_time.weekday() >= 5
        
        # Simulate fulfilled or not based on fake previous inventory
        inv_before = random.randint(0, 50)
        stockout = qty > inv_before
        fulfilled = not stockout and random.random() > 0.1 # 10% random fail
        
        order = HistoricalOrder(
            order_id=str(uuid.uuid4())[:8],
            timestamp=order_time,
            product_id=product.id,
            store_id=store.id,
            quantity=qty,
            customer_lat=store.latitude + random.uniform(-0.02, 0.02),
            customer_lng=store.longitude + random.uniform(-0.02, 0.02),
            hour=order_time.hour,
            day_of_week=order_time.weekday(),
            month=order_time.month,
            is_weekend=is_weekend,
            promotion_flag=random.random() > 0.8,
            inventory_before_order=inv_before,
            inventory_after_order=inv_before - qty if fulfilled else inv_before,
            fulfilled=fulfilled,
            cancelled=False,
            stockout=stockout
        )
        batch.append(order)
        
        if len(batch) >= batch_size:
            session.add_all(batch)
            await session.flush()
            batch = []
            print(f"Generated {i+1}/{num_orders} orders...")
            
    if batch:
        session.add_all(batch)
        await session.flush()

async def create_seed_users(session, stores):
    print("Creating seed users...")
    admin = User(
        email="admin@fulfilliq.local",
        hashed_password=get_password_hash("admin123"),
        role=RoleEnum.PLATFORM_ADMIN
    )
    manager = User(
        email="manager01@fulfilliq.local",
        hashed_password=get_password_hash("manager123"),
        role=RoleEnum.STORE_MANAGER,
        store_id=stores[0].id
    )
    customer = User(
        email="customer@fulfilliq.local",
        hashed_password=get_password_hash("customer123"),
        role=RoleEnum.CUSTOMER
    )
    session.add_all([admin, manager, customer])

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        stores = await generate_stores(session, 50)
        products = await generate_products(session, 500)
        await generate_inventory(session, stores, products)
        await create_seed_users(session, stores)
        await generate_orders(session, stores, products, num_orders=30000, days=90)
        await session.commit()
        print("Data generation complete!")

if __name__ == "__main__":
    asyncio.run(main())
