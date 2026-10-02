import asyncio
import asyncpg
import json
import random

async def main():
    unsplash_map = {
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
        
    import os
    db_url = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://fulfilliq_user:fulfilliq_dev_only@postgres:5432/fulfilliq_db').replace('+asyncpg', '')
    conn = await asyncpg.connect(db_url)
    for cat, imgs in unsplash_map.items():
        rows = await conn.fetch('SELECT id FROM products WHERE category = $1', cat)
        for r in rows:
            img = random.choice(imgs)
            await conn.execute('UPDATE products SET image_url = $1 WHERE id = $2', img, r['id'])
    
    print('Updated image variety for all categories!')
    await conn.close()

asyncio.run(main())
