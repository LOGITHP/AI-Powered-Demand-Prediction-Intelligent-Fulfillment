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

    UNSPLASH_MAP = {
        "Grocery": [
            "https://images.unsplash.com/photo-1584473457406-6240486418e9?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1574316071802-0d684efa7ba5?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1542838132-92c53300491e?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1588964895597-cfccd6e2dbf9?w=480&h=360&fit=crop",
        ],
        "Beverages": [
            "https://images.unsplash.com/photo-1622543925917-763c34d1a86e?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1556881286-fc6915169721?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=480&h=360&fit=crop",
        ],
        "Personal Care": [
            "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1608248593842-8021c6a8ba7c?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1556228720-192a6af4e86e?w=480&h=360&fit=crop",
        ],
        "Household": [
            "https://images.unsplash.com/photo-1584824486509-112e4181f1ce?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1585421514738-01798e348b17?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1563453392212-326f5e854473?w=480&h=360&fit=crop",
        ],
        "Electronics": [
            "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=480&h=360&fit=crop",
        ],
        "Stationery": [
            "https://images.unsplash.com/photo-1503694978374-8a2fa686963a?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1497005367839-6e852de72767?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1568227493940-a386a3d6f788?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=480&h=360&fit=crop",
        ],
        "Snacks": [
            "https://images.unsplash.com/photo-1621939514649-280e2ee25f60?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1599490659213-e2b9527bd087?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1577968897966-3d4325b36b61?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1582281271083-ecce338d8393?w=480&h=360&fit=crop",
        ],
        "Fruits": [
            "https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1528825871115-3581a5387919?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1550258987-190a2d41a8ba?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1490885578174-acda8905c2c6?w=480&h=360&fit=crop",
        ],
        "Vegetables": [
            "https://images.unsplash.com/photo-1566385101042-1a0aa0c1268c?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1518843875459-f738682238a6?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1557844352-761f2565b576?w=480&h=360&fit=crop",
        ],
        "Baby Care": [
            "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1522771930-78848d9293e8?w=480&h=360&fit=crop",
        ],
        "Pet Care": [
            "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1623387641168-d9803ddd3f35?w=480&h=360&fit=crop",
        ],
        "Kitchen": [
            "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1581622558667-3419a8dc5f83?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1590794055456-0efb3fde9b8e?w=480&h=360&fit=crop",
        ],
        "Health & Wellness": [
            "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1584308666744-24d5e4a8b792?w=480&h=360&fit=crop",
            "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=480&h=360&fit=crop",
        ],
    }
    products: list[dict] = []
    products.append({
        "id": 1, "sku": "FIQ-ELE-0001", "name": "Wireless Mouse", "category": "Electronics",
        "subcategory": "Computer accessories", "brand": "Orbit Works", "price": 649.0,
        "unit": "1 unit", "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=480&h=360&fit=crop", "is_active": True,
    })
    pid = 2
    for category, (names_csv, subs) in CATALOG.items():
        names = [name.strip() for name in names_csv.split(",")]
        img_list = UNSPLASH_MAP.get(category, ["https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=480&h=360&fit=crop"])
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
                "image_url": rng.choice(img_list),
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
    SOURCES = ["POS", "WMS", "ERP", "RFID"]
    EVENT_TYPES = {
        "POS":  ["sale", "return", "void"],
        "WMS":  ["replenishment", "pick", "putaway", "cycle_count", "damage"],
        "ERP":  ["purchase_receipt", "adjustment", "write_off", "transfer_in", "transfer_out"],
        "RFID": ["scan_observation", "zone_count", "tag_read"],
    }

    for inventory in inventory_rows:
        sid = inventory["store_id"]
        pid = inventory["product_id"]
        base_qty = inventory["reported_quantity"]

        # --- POS events: customer sales, occasional returns ---
        num_pos = rng.randint(2, 8)
        for _ in range(num_pos):
            etype = rng.choices(["sale", "return", "void"], weights=[85, 10, 5])[0]
            delta = -rng.randint(1, 3) if etype == "sale" else rng.randint(1, 2)
            ts = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            event_rows.append({
                "store_id": sid, "product_id": pid,
                "event_type": etype, "source": "POS", "quantity_delta": delta,
                "reported_quantity": max(0, base_qty + delta),
                "note": f"POS terminal #{rng.randint(1, 6)} — store {sid}",
                "created_at": ts,
            })

        # --- WMS events: warehouse picks, putaway, replenishment, damage ---
        num_wms = rng.randint(1, 5)
        for _ in range(num_wms):
            etype = rng.choices(["replenishment", "pick", "putaway", "cycle_count", "damage"], weights=[35, 25, 20, 12, 8])[0]
            if etype in ("replenishment", "putaway"):
                delta = rng.randint(3, 15)
            elif etype == "cycle_count":
                delta = 0
            else:
                delta = -rng.randint(1, 4)
            # WMS sometimes reports a different quantity than POS (the core reconciliation problem)
            wms_reported = max(0, base_qty + rng.randint(-3, 3))
            ts = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23))
            # Inject sync delay: WMS events sometimes lag behind POS by 1-4 hours
            ts = ts + timedelta(hours=rng.randint(0, 4))
            event_rows.append({
                "store_id": sid, "product_id": pid,
                "event_type": etype, "source": "WMS", "quantity_delta": delta,
                "reported_quantity": wms_reported,
                "note": f"WMS rack {rng.choice('ABCDEF')}-{rng.randint(1, 30):02d} — store {sid}",
                "created_at": ts,
            })

        # --- ERP events: purchase receipts, adjustments, write-offs, transfers ---
        num_erp = rng.randint(1, 3)
        for _ in range(num_erp):
            etype = rng.choices(["purchase_receipt", "adjustment", "write_off", "transfer_in", "transfer_out"], weights=[40, 25, 10, 15, 10])[0]
            if etype in ("purchase_receipt", "transfer_in"):
                delta = rng.randint(5, 25)
            elif etype == "adjustment":
                delta = rng.randint(-5, 5)
            else:
                delta = -rng.randint(1, 8)
            # ERP can have stale data — its reported quantity may differ from POS & WMS
            erp_reported = max(0, base_qty + rng.randint(-4, 4))
            ts = now - timedelta(days=rng.randint(0, 90), hours=rng.randint(0, 23))
            event_rows.append({
                "store_id": sid, "product_id": pid,
                "event_type": etype, "source": "ERP", "quantity_delta": delta,
                "reported_quantity": erp_reported,
                "note": f"ERP batch {rng.randint(10000, 99999)} — store {sid}",
                "created_at": ts,
            })

        # --- RFID events: tag reads, zone scans, observations ---
        num_rfid = rng.randint(1, 4)
        for _ in range(num_rfid):
            etype = rng.choices(["scan_observation", "zone_count", "tag_read"], weights=[45, 30, 25])[0]
            # RFID observation: no delta, just a physical count observation
            rfid_observed = max(0, base_qty + rng.randint(-5, 2))  # RFID often reads lower (missed tags)
            ts = now - timedelta(days=rng.randint(0, 30), hours=rng.randint(0, 23))
            event_rows.append({
                "store_id": sid, "product_id": pid,
                "event_type": etype, "source": "RFID", "quantity_delta": 0,
                "reported_quantity": rfid_observed,
                "note": f"RFID reader zone-{rng.choice('ABCDEFGH')}{rng.randint(1, 4)} — store {sid}",
                "created_at": ts,
            })

        # --- Inject realistic errors for ~15% of inventory items ---
        if rng.random() < 0.15:
            # Duplicate event (same event sent twice by POS)
            dup = event_rows[-rng.randint(1, min(3, len(event_rows)))]
            event_rows.append({**dup, "note": f"DUPLICATE — {dup.get('note', '')}"})

        if rng.random() < 0.10:
            # Missing event gap: WMS shows replenishment but POS never recorded the stock arriving
            event_rows.append({
                "store_id": sid, "product_id": pid,
                "event_type": "replenishment", "source": "WMS", "quantity_delta": rng.randint(5, 15),
                "reported_quantity": base_qty + rng.randint(5, 15),
                "note": f"MISSING_POS_RECEIPT — WMS recorded but POS did not reflect — store {sid}",
                "created_at": now - timedelta(days=rng.randint(1, 30)),
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
