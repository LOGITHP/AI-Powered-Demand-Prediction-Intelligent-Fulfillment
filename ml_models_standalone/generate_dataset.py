import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_dataset(num_records=10000):
    print(f"Generating {num_records} simulated historical orders...")
    records = []
    
    # 50 stores, 500 products
    store_ids = list(range(1, 51))
    product_ids = list(range(1, 501))
    
    start_date = datetime.now() - timedelta(days=90)
    
    for _ in range(num_records):
        store_id = random.choice(store_ids)
        product_id = random.choice(product_ids)
        
        # Temporal features
        timestamp = start_date + timedelta(days=random.randint(0, 90), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        month = timestamp.month
        is_weekend = 1 if day_of_week >= 5 else 0
        promotion_flag = 1 if random.random() < 0.1 else 0  # 10% chance of promo
        
        # Demand Generation Logic
        base_demand = random.randint(1, 5)
        if is_weekend:
            base_demand += random.randint(1, 3)
        if promotion_flag:
            base_demand = int(base_demand * 1.5)
        if 17 <= hour <= 20: # Evening rush
            base_demand += random.randint(1, 4)
            
        quantity_demanded = base_demand
        
        # Inventory State before order
        # Simulate that sometimes inventory is high, sometimes low
        inventory_before_order = random.randint(0, 50)
        inventory_accuracy = round(random.uniform(0.6, 1.0), 2)
        inventory_age_hours = round(random.uniform(0.1, 72.0), 1)
        sales_velocity = round(random.uniform(0.1, 5.0), 2)
        
        # Target Variable for Availability Model
        # Was the order successfully fulfilled?
        # Logic: If they wanted X, and we actually had X (factoring in accuracy), it's fulfilled.
        actual_inventory = int(inventory_before_order * inventory_accuracy)
        fulfilled = 1 if actual_inventory >= quantity_demanded else 0
        
        records.append({
            "store_id": store_id,
            "product_id": product_id,
            "hour": hour,
            "day_of_week": day_of_week,
            "month": month,
            "is_weekend": is_weekend,
            "promotion_flag": promotion_flag,
            "inventory_before_order": inventory_before_order,
            "inventory_accuracy": inventory_accuracy,
            "inventory_age_hours": inventory_age_hours,
            "sales_velocity": sales_velocity,
            "quantity_demanded": quantity_demanded,
            "fulfilled": fulfilled
        })

    df = pd.DataFrame(records)
    output_file = "historical_orders.csv"
    df.to_csv(output_file, index=False)
    print(f"Dataset generated successfully: {output_file}")
    print(df.head())

if __name__ == "__main__":
    # Generate 50,000 rows for good training
    generate_dataset(50000)
