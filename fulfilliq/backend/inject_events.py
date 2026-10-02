"""Inject multi-source POS/WMS/ERP/RFID events into the running database."""
import asyncio, random
from datetime import datetime, timedelta
from sqlalchemy import insert, select
from app.core.database import AsyncSessionLocal
from app.models.all_models import Inventory, InventoryEvent

async def inject():
    rng = random.Random(42)
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        rows = (await session.scalars(select(Inventory))).all()
        events = []
        for inv in rows:
            sid, pid, base_qty = inv.store_id, inv.product_id, inv.reported_quantity

            # ERP events
            for _ in range(rng.randint(1, 3)):
                etype = rng.choices(["purchase_receipt","adjustment","write_off","transfer_in","transfer_out"], weights=[40,25,10,15,10])[0]
                if etype in ("purchase_receipt","transfer_in"):
                    delta = rng.randint(5, 25)
                elif etype == "adjustment":
                    delta = rng.randint(-5, 5)
                else:
                    delta = -rng.randint(1, 8)
                events.append({
                    "store_id": sid, "product_id": pid,
                    "event_type": etype, "source": "ERP", "quantity_delta": delta,
                    "reported_quantity": max(0, base_qty + rng.randint(-4, 4)),
                    "note": f"ERP batch {rng.randint(10000,99999)} — store {sid}",
                    "created_at": now - timedelta(days=rng.randint(0,90), hours=rng.randint(0,23)),
                })

            # WMS events
            for _ in range(rng.randint(1, 4)):
                etype = rng.choices(["replenishment","pick","putaway","cycle_count","damage"], weights=[35,25,20,12,8])[0]
                if etype in ("replenishment","putaway"):
                    delta = rng.randint(3, 15)
                elif etype == "cycle_count":
                    delta = 0
                else:
                    delta = -rng.randint(1, 4)
                events.append({
                    "store_id": sid, "product_id": pid,
                    "event_type": etype, "source": "WMS", "quantity_delta": delta,
                    "reported_quantity": max(0, base_qty + rng.randint(-3, 3)),
                    "note": f"WMS rack {rng.choice('ABCDEF')}-{rng.randint(1,30):02d} — store {sid}",
                    "created_at": now - timedelta(days=rng.randint(0,60), hours=rng.randint(0,23)) + timedelta(hours=rng.randint(0,4)),
                })

            # RFID events
            for _ in range(rng.randint(1, 3)):
                etype = rng.choices(["scan_observation","zone_count","tag_read"], weights=[45,30,25])[0]
                events.append({
                    "store_id": sid, "product_id": pid,
                    "event_type": etype, "source": "RFID", "quantity_delta": 0,
                    "reported_quantity": max(0, base_qty + rng.randint(-5, 2)),
                    "note": f"RFID reader zone-{rng.choice('ABCDEFGH')}{rng.randint(1,4)} — store {sid}",
                    "created_at": now - timedelta(days=rng.randint(0,30), hours=rng.randint(0,23)),
                })

            # Inject realistic errors
            if rng.random() < 0.15 and events:
                dup = events[-rng.randint(1, min(3, len(events)))]
                events.append({**dup, "note": f"DUPLICATE — {dup.get('note','')}"})
            if rng.random() < 0.10:
                events.append({
                    "store_id": sid, "product_id": pid,
                    "event_type": "replenishment", "source": "WMS", "quantity_delta": rng.randint(5,15),
                    "reported_quantity": base_qty + rng.randint(5, 15),
                    "note": f"MISSING_POS_RECEIPT — WMS recorded but POS did not reflect — store {sid}",
                    "created_at": now - timedelta(days=rng.randint(1,30)),
                })

        await session.execute(insert(InventoryEvent), events)
        await session.commit()
        print(f"Injected {len(events)} multi-source events across {len(rows)} inventory positions")

asyncio.run(inject())
