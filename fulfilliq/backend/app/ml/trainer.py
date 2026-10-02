import os
import joblib
import pandas as pd
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score, f1_score
from app.models.all_models import HistoricalOrder, ModelVersion
from app.core.config import settings
import json

async def fetch_training_data(db: AsyncSession, sample_fraction: float):
    # For a real app, you'd want to stream this or use pandas read_sql. 
    # For prototype, we'll fetch via sqlalchemy and convert to dataframe.
    result = await db.execute(select(HistoricalOrder))
    orders = result.scalars().all()
    
    df = pd.DataFrame([{
        "hour": o.hour,
        "day_of_week": o.day_of_week,
        "product_id": o.product_id,
        "store_id": o.store_id,
        "inventory_before": o.inventory_before_order,
        "quantity": o.quantity,
        "fulfilled": int(o.fulfilled) if o.fulfilled else 0
    } for o in orders])
    
    if len(df) > 0 and sample_fraction < 1.0:
        df = df.sample(frac=sample_fraction, random_state=42)
    return df

async def train_demand_model(db: AsyncSession, sample_fraction: float = 1.0):
    df = await fetch_training_data(db, sample_fraction)
    if len(df) < 100:
        print("Not enough data to train demand model")
        return
        
    # Features for demand: hour, day, product, store
    # Target: quantity (assuming we group by hour/store/product to get total demand, 
    # but for simplicity we'll just predict the quantity of an order given features)
    # A better approach is aggregating by hour, but we will use raw for prototype.
    
    X = df[["hour", "day_of_week", "product_id", "store_id"]]
    y = df["quantity"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = HistGradientBoostingRegressor()
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    
    version = f"demand_v_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    filepath = os.path.join(settings.MODEL_STORAGE_PATH, "demand", f"{version}.pkl")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    joblib.dump(model, filepath)
    
    metrics = {"mae": mae}
    mv = ModelVersion(
        model_type="DEMAND",
        version_name=version,
        file_path=filepath,
        dataset_size=len(df),
        is_active=True,
        metrics=json.dumps(metrics),
        features=json.dumps(list(X.columns))
    )
    db.add(mv)
    await db.commit()

async def train_availability_model(db: AsyncSession, sample_fraction: float = 1.0):
    df = await fetch_training_data(db, sample_fraction)
    if len(df) < 100:
        print("Not enough data to train availability model")
        return
        
    # Target: fulfilled (1 or 0)
    X = df[["hour", "day_of_week", "product_id", "store_id", "inventory_before", "quantity"]]
    y = df["fulfilled"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = HistGradientBoostingClassifier()
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, zero_division=0)
    
    version = f"availability_v_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    filepath = os.path.join(settings.MODEL_STORAGE_PATH, "availability", f"{version}.pkl")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    joblib.dump(model, filepath)
    
    metrics = {"accuracy": acc, "f1": f1}
    mv = ModelVersion(
        model_type="AVAILABILITY",
        version_name=version,
        file_path=filepath,
        dataset_size=len(df),
        is_active=True,
        metrics=json.dumps(metrics),
        features=json.dumps(list(X.columns))
    )
    db.add(mv)
    await db.commit()
