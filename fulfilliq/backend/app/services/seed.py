from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.all_models import (
    HistoricalOrder, Inventory, InventoryEvent, Order, OrderItem, Product,
    Recommendation, RoleEnum, SimulationState, Store, StoreTypeEnum, User,
)

AREAS = [
    ("Gandhipuram", 11.0183, 76.9674), ("RS Puram", 11.0098, 76.9531),
    ("Peelamedu", 11.0256, 77.0042), ("Saibaba Colony", 11.0251, 76.9446),
    ("Singanallur", 11.0004, 77.0288), ("Ramanathapuram", 10.9994, 76.9906),
    ("Ukkadam", 10.9937, 76.9615), ("Kuniyamuthur", 10.9464, 76.9495),
    ("Saravanampatti", 11.0805, 77.0011), ("Kalapatti", 11.0797, 77.0376),
    ("Ganapathy", 11.0452, 76.9868), ("Vadavalli", 11.0351, 76.9079),
    ("Sundarapuram", 10.9636, 76.9751), ("Podanur", 10.9628, 76.9942),
    ("Town Hall", 10.9965, 76.9629),
]

CATALOG = {
    "Grocery": ("Rice, Toor Dal, Whole Wheat Flour, Rolled Oats, Chickpeas, Sunflower Oil, Sugar, Sea Salt", ["Staples", "Pulses"]),
    "Beverages": ("Filter Coffee, Green Tea, Mango Drink, Sparkling Water, Cocoa Mix, Ginger Tea", ["Coffee", "Tea"]),
    "Personal Care": ("Herbal Shampoo, Aloe Body Wash, Daily Moisturizer, Neem Face Cleanser, Hand Cream", ["Bath", "Skin care"]),
    "Household": ("Laundry Liquid, Dish Soap, Microfiber Cloth, Surface Cleaner, Storage Bags", ["Cleaning", "Storage"]),
    "Electronics": ("Wireless Mouse, USB-C Cable, Desk Lamp, Bluetooth Speaker, Power Bank, Keyboard", ["Accessories", "Computer"]),
    "Stationery": ("Notebook, Gel Pen Set, Sketch Pad, Sticky Notes, Document Folder", ["Writing", "Paper"]),
    "Snacks": ("Roasted Cashews, Millet Crisps, Dark Chocolate, Trail Mix, Potato Wafers", ["Savory", "Sweet"]),
    "Fruits": ("Alphonso Mango, Bananas, Green Apples, Sweet Lime, Pomegranate", ["Fresh fruit"]),
    "Vegetables": ("Tomatoes, Red Onion, Baby Spinach, Green Chilli, Potatoes", ["Fresh vegetables"]),
    "Baby Care": ("Soft Baby Wipes, Gentle Baby Lotion, Cotton Buds, Feeding Bottle", ["Care"]),
    "Pet Care": ("Dry Cat Food, Dog Chew Bites, Pet Shampoo, Litter Pellets", ["Food", "Care"]),
    "Kitchen": ("Steel Water Bottle, Mixing Bowl, Wooden Spatula, Food Container, Peeler", ["Tools", "Storage"]),
    "Health & Wellness": ("Vitamin C Tablets, Digital Thermometer, Yoga Strap, Protein Blend", ["Wellness", "Fitness"]),
}
BRANDS = ["Everyday Co.", "Field & Form", "Brightwell", "Northstar", "Goodroot", "Homecraft", "Orbit Works"]


async def seed_database(session: AsyncSession) -> None:
    existing = await session.scalar(select(func.count(Store.id)))
    if existing:
        manager_store = await session.scalar(select(Store.id).order_by(Store.id).limit(1))
        demo_users = [
            ("admin@fulfilliq.local", "FulfillIQ-demo-2026!", RoleEnum.PLATFORM_ADMIN, None),
            ("manager01@fulfilliq.local", "FulfillIQ-demo-2026!", RoleEnum.STORE_MANAGER, manager_store),
            ("customer@fulfilliq.local", "FulfillIQ-demo-2026!", RoleEnum.CUSTOMER, None),
        ]
        for email, password, role, store_id in demo_users:
            demo_user = await session.scalar(select(User).where(User.email == email))
            if demo_user:
                demo_user.hashed_password = get_password_hash(password)
                demo_user.role = role
                demo_user.store_id = store_id
            else:
                session.add(User(email=email, hashed_password=get_password_hash(password), role=role, store_id=store_id))
        if not await session.get(SimulationState, 1):
            session.add(SimulationState(id=1, simulated_at=datetime.utcnow(), seed=settings.SEED, is_running=False))
        await session.commit()
        return

    rng = random.Random(settings.SEED)
    stores: list[dict] = []
    for i in range(1, 51):
        area, lat, lng = AREAS[(i - 1) % len(AREAS)]
        stores.append({
            "id": i, "name": f"FulfillIQ Store {i:03d}",
            "type": [StoreTypeEnum.RETAIL_STORE, StoreTypeEnum.DARK_STORE, StoreTypeEnum.WAREHOUSE][(i - 1) % 3],
            "latitude": lat + rng.uniform(-0.009, 0.009), "longitude": lng + rng.uniform(-0.010, 0.010),
            "area": area, "address": f"{rng.randint(1, 220)} {area} Main Road, Coimbatore, Tamil Nadu",
            "operating_hours": "7:00 AM – 11:00 PM", "capacity": rng.randint(900, 2400), "is_active": True,
        })
    await session.execute(insert(Store), stores)

    products: list[dict] = []
    products.append({
        "id": 1, "sku": "FIQ-ELE-0001", "name": "Wireless Mouse", "category": "Electronics",
        "subcategory": "Computer accessories", "brand": "Orbit Works", "price": 649.0,
        "unit": "1 unit", "image_url": "https://placehold.co/480x360/f4f3ef/334155?text=Wireless+Mouse", "is_active": True,
    })
    pid = 2
    for category, (names_csv, subs) in CATALOG.items():
        names = [name.strip() for name in names_csv.split(",")]
        for n in range(1, 40):
            base = names[(n - 1) % len(names)]
            variant = (n - 1) // len(names)
            name = base if variant == 0 else f"{base} {['Classic', 'Select', 'Family Pack', 'Plus'][variant % 4]}"
            if name == "Wireless Mouse":
                name = "Wireless Mouse Lite"
            products.append({
                "id": pid, "sku": f"FIQ-{category[:3].upper()}-{pid:04d}", "name": name,
                "category": category, "subcategory": subs[(n - 1) % len(subs)],
                "brand": BRANDS[(pid * 3) % len(BRANDS)], "price": round(rng.uniform(29, 2499), 2),
                "unit": rng.choice(["1 unit", "250 g", "500 g", "1 pack", "1 L"]),
                "image_url": f"https://placehold.co/480x360/f4f3ef/334155?text={category.replace(' ', '+')}",
                "is_active": True,
            })
            pid += 1
    await session.execute(insert(Product), products)

    inventory_rows: list[dict] = []
    now = datetime.utcnow()
    for store in stores:
        for product in products:
            if product["id"] != 1 and rng.random() > 0.64:
                continue
            qty = rng.randint(2, 38)
            accuracy = round(rng.uniform(0.72, 0.99), 2)
            if product["id"] == 1:
                if store["id"] == 4:
                    qty, accuracy = 3, 0.68
                elif store["id"] == 17:
                    qty, accuracy = 17, 0.97
                elif store["id"] == 23:
                    qty, accuracy = 8, 0.86
            inventory_rows.append({
                "store_id": store["id"], "product_id": product["id"],
                "reported_quantity": qty, "reserved_quantity": rng.randint(0, min(3, qty)),
                "last_updated": now - timedelta(minutes=rng.randint(1, 180)),
                "reorder_level": rng.randint(7, 13), "safety_stock": rng.randint(3, 7),
                "inventory_accuracy": accuracy,
            })
    await session.execute(insert(Inventory), inventory_rows)

    users = [
        User(email="admin@fulfilliq.local", hashed_password=get_password_hash("FulfillIQ-demo-2026!"), role=RoleEnum.PLATFORM_ADMIN),
        User(email="manager01@fulfilliq.local", hashed_password=get_password_hash("FulfillIQ-demo-2026!"), role=RoleEnum.STORE_MANAGER, store_id=1),
        User(email="customer@fulfilliq.local", hashed_password=get_password_hash("FulfillIQ-demo-2026!"), role=RoleEnum.CUSTOMER),
    ]
    session.add_all(users)
    await session.flush()

    hist: list[dict] = []
    products_by_id = {p["id"]: p for p in products}
    stores_by_id = {s["id"]: s for s in stores}
    for ix in range(settings.HISTORICAL_ORDER_COUNT):
        store_id = rng.randint(1, 50)
        product_id = rng.randint(1, len(products))
        product = products_by_id[product_id]
        store = stores_by_id[store_id]
        timestamp = now - timedelta(days=rng.random() * 90, hours=rng.random() * 24)
        hour = timestamp.hour
        dow = timestamp.weekday()
        category_factor = 1.4 if product["category"] in ("Grocery", "Beverages", "Snacks", "Fruits", "Vegetables") else 0.75
        hour_factor = 1.55 if hour in (8, 9, 12, 18, 19, 20) else (0.38 if hour < 7 or hour > 22 else 0.85)
        weekend_factor = 1.28 if dow >= 5 else 1.0
        seasonal_factor = 1.12 if timestamp.month in (4, 5, 6, 10, 11, 12) else 1.0
        local_factor = 1.2 if store["area"] in ("Gandhipuram", "Peelamedu", "RS Puram") else 1.0
        velocity = round(category_factor * hour_factor * weekend_factor * seasonal_factor * local_factor, 3)
        qty = max(1, min(8, int(rng.expovariate(1 / max(1.3, 1.9 * velocity))) + 1))
        accuracy = rng.uniform(0.69, 0.99)
        age = rng.expovariate(1 / 2.8)
        stock = max(0, int(rng.gauss(13 * velocity, 7)))
        fulfilled = stock >= qty and rng.random() < min(0.99, 0.72 + accuracy * 0.23 - max(0, age - 3) * 0.025)
        stockout = stock < qty or (not fulfilled and rng.random() < 0.7)
        promotion = rng.random() < 0.14
        hist.append({
            "order_id": f"H{ix + 1:07d}", "timestamp": timestamp, "product_id": product_id,
            "store_id": store_id, "quantity": qty,
            "customer_lat": store["latitude"] + rng.uniform(-0.06, 0.06),
            "customer_lng": store["longitude"] + rng.uniform(-0.06, 0.06),
            "hour": hour, "day_of_week": dow, "month": timestamp.month, "is_weekend": dow >= 5,
            "promotion_flag": promotion, "inventory_before_order": stock,
            "inventory_after_order": max(0, stock - qty) if fulfilled else stock,
            "fulfilled": fulfilled, "cancelled": not fulfilled, "stockout": stockout,
            "inventory_accuracy": round(accuracy, 3), "inventory_age_hours": round(age, 3),
            "sales_velocity": velocity * (1.18 if promotion else 1.0),
        })
    await session.execute(insert(HistoricalOrder), hist)

    event_rows = []
    for _ in range(1600):
        inventory = rng.choice(inventory_rows)
        delta = rng.choice([-4, -2, -1, 1, 3, 6, 10])
        event_rows.append({
            "store_id": inventory["store_id"], "product_id": inventory["product_id"],
            "event_type": "sale" if delta < 0 else "replenishment", "quantity_delta": delta,
            "note": "Generated historical inventory event", "created_at": now - timedelta(days=rng.randint(0, 90)),
        })
    await session.execute(insert(InventoryEvent), event_rows)

    session.add(Recommendation(
        store_id=23, product_id=1, action_type="STOCK_TRANSFER", recommended_quantity=9,
        deadline=now + timedelta(hours=1),
        reason="Forecast demand is above on-hand stock plus safety stock at this location.",
        status="PENDING",
    ))
    session.add(SimulationState(id=1, simulated_at=now, seed=settings.SEED, is_running=False))

    # A few seeded demo orders make the order and operations views useful on first login.
    for index in range(8):
        store_id = rng.randint(1, 50)
        product_id = rng.randint(1, 30)
        order = Order(
            customer_id=users[2].id, store_id=store_id, customer_lat=stores_by_id[store_id]["latitude"] + 0.006,
            customer_lng=stores_by_id[store_id]["longitude"] - 0.004, status=["CONFIRMED", "PREPARING", "OUT_FOR_DELIVERY"][index % 3],
            total_amount=products_by_id[product_id]["price"],
        )
        order.items.append(OrderItem(product_id=product_id, quantity=1, price_at_time=products_by_id[product_id]["price"]))
        session.add(order)
    await session.commit()


async def generate_historical_data(session: AsyncSession, count: int, seed: int = 42) -> int:
    """Append reproducible, time- and location-sensitive simulated order examples."""
    rng = random.Random(seed)
    stores = (await session.scalars(select(Store))).all()
    products = (await session.scalars(select(Product))).all()
    if not stores or not products or count < 1:
        return 0
    now = datetime.utcnow()
    rows: list[dict] = []
    for ix in range(count):
        store = stores[rng.randrange(len(stores))]
        product = products[rng.randrange(len(products))]
        timestamp = now - timedelta(days=rng.random() * 90, hours=rng.random() * 24)
        hour, dow = timestamp.hour, timestamp.weekday()
        category = product.category
        c_factor = 1.4 if category in ("Grocery", "Beverages", "Snacks", "Fruits", "Vegetables") else 0.78
        h_factor = 1.5 if hour in (8, 9, 12, 18, 19, 20) else (0.4 if hour < 7 or hour > 22 else 0.86)
        velocity = c_factor * h_factor * (1.25 if dow >= 5 else 1.0) * (1.18 if rng.random() < 0.14 else 1.0)
        qty = max(1, min(8, int(rng.expovariate(1 / max(1.2, 1.8 * velocity))) + 1))
        stock = max(0, int(rng.gauss(13 * velocity, 7)))
        accuracy, age = rng.uniform(0.68, 0.99), rng.expovariate(1 / 2.8)
        fulfilled = stock >= qty and rng.random() < min(0.99, 0.72 + accuracy * 0.23 - max(0, age - 3) * 0.025)
        rows.append({
            "order_id": f"G{seed}-{ix}-{rng.randrange(999999)}", "timestamp": timestamp,
            "product_id": product.id, "store_id": store.id, "quantity": qty,
            "customer_lat": store.latitude + rng.uniform(-0.06, 0.06), "customer_lng": store.longitude + rng.uniform(-0.06, 0.06),
            "hour": hour, "day_of_week": dow, "month": timestamp.month, "is_weekend": dow >= 5,
            "promotion_flag": velocity > c_factor * h_factor, "inventory_before_order": stock,
            "inventory_after_order": max(0, stock - qty) if fulfilled else stock, "fulfilled": fulfilled,
            "cancelled": not fulfilled, "stockout": stock < qty or (not fulfilled and rng.random() < 0.7),
            "inventory_accuracy": round(accuracy, 3), "inventory_age_hours": round(age, 3),
            "sales_velocity": round(velocity, 3),
        })
    await session.execute(insert(HistoricalOrder), rows)
    await session.commit()
    return len(rows)
