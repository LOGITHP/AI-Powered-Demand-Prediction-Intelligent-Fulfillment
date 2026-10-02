from __future__ import annotations

import json
import math
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import and_, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.all_models import (
    AvailabilityPrediction, DemandPrediction, HistoricalOrder, Inventory, InventoryEvent,
    ModelVersion, Order, OrderItem, Product, Recommendation, RoleEnum, SimulationState,
    Store, StoreTransfer, StoreTypeEnum, User,
)
from app.services.seed import generate_historical_data, seed_database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
DEMAND_FEATURES = ["product_id", "store_id", "hour", "day_of_week", "month", "is_weekend", "promotion_flag", "inventory_before_order"]
AVAILABILITY_FEATURES = ["inventory_before_order", "quantity", "inventory_accuracy", "inventory_age_hours", "sales_velocity", "hour", "day_of_week", "store_id", "product_id"]
ACTIVE_MODELS: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    yield


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", description="Simulated retail availability and fulfillment platform.", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterInput(BaseModel):
    email: str
    password: str = Field(min_length=10)
    role: RoleEnum = RoleEnum.CUSTOMER
    store_id: int | None = None


class RecommendationInput(BaseModel):
    product_id: int
    customer_lat: float
    customer_lng: float
    quantity: int = Field(default=1, ge=1, le=99)
    radius_km: float = Field(default=18, ge=1, le=80)


class DemandInput(BaseModel):
    product_id: int
    store_id: int
    hour: int = Field(default_factory=lambda: datetime.now().hour, ge=0, le=23)
    day_of_week: int = Field(default_factory=lambda: datetime.now().weekday(), ge=0, le=6)
    promotion_flag: bool = False


class AvailabilityInput(BaseModel):
    product_id: int
    store_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class OrderLineInput(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=99)


class OrderInput(BaseModel):
    store_id: int
    customer_lat: float
    customer_lng: float
    items: list[OrderLineInput] = Field(min_length=1)


class InventoryUpdate(BaseModel):
    reported_quantity: int = Field(ge=0)
    note: str = "Manual stock count"


class GenerateInput(BaseModel):
    historical_orders: int = Field(default=30000, ge=100, le=100000)
    seed: int = 42


class FulfillmentWeightInput(BaseModel):
    availability: int = Field(ge=0, le=100)
    inventory: int = Field(ge=0, le=100)
    distance: int = Field(ge=0, le=100)
    future_availability: int = Field(ge=0, le=100)
    delivery_sla: int = Field(ge=0, le=100)


class StoreCreate(BaseModel):
    name: str
    type: StoreTypeEnum
    latitude: float
    longitude: float
    area: str
    address: str
    capacity: int = 1000


class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str
    subcategory: str = "General"
    brand: str = "FulfillIQ Select"
    price: float = Field(ge=0)
    unit: str = "1 unit"


class TransferInput(BaseModel):
    from_store_id: int
    to_store_id: int
    product_id: int
    quantity: int = Field(ge=1)


def require_roles(*roles: RoleEnum):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return user
    return dependency


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_error = HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        raise credentials_error
    user = await db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def require_store_access(user: User, store_id: int) -> None:
    if user.role == RoleEnum.STORE_MANAGER and user.store_id != store_id:
        raise HTTPException(status_code=403, detail="Store managers can only access their assigned store.")


def user_payload(user: User) -> dict[str, Any]:
    return {"id": user.id, "email": user.email, "role": user.role.value, "store_id": user.store_id}


def product_payload(product: Product) -> dict[str, Any]:
    return {
        "id": product.id, "sku": product.sku, "name": product.name, "category": product.category,
        "subcategory": product.subcategory, "brand": product.brand, "price": product.price,
        "unit": product.unit, "image_url": product.image_url, "is_active": product.is_active,
    }


def store_payload(store: Store) -> dict[str, Any]:
    return {
        "id": store.id, "name": store.name, "type": store.type.value, "latitude": store.latitude,
        "longitude": store.longitude, "area": store.area, "address": store.address,
        "operating_hours": store.operating_hours, "capacity": store.capacity, "is_active": store.is_active,
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    delta_p, delta_l = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    value = math.sin(delta_p / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(delta_l / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def logistic(value: float) -> float:
    return 1 / (1 + math.exp(-max(-25, min(25, value))))


DEFAULT_SCORE_WEIGHTS = {
    "availability": 40, "inventory": 20, "distance": 20,
    "future_availability": 10, "delivery_sla": 10,
}


async def fulfillment_weights(db: AsyncSession) -> dict[str, int]:
    state = await db.get(SimulationState, 1)
    if not state or not state.fulfillment_weights:
        return DEFAULT_SCORE_WEIGHTS.copy()
    try:
        saved = json.loads(state.fulfillment_weights)
        return {name: int(saved.get(name, value)) for name, value in DEFAULT_SCORE_WEIGHTS.items()}
    except (TypeError, ValueError, json.JSONDecodeError):
        return DEFAULT_SCORE_WEIGHTS.copy()


async def active_model(db: AsyncSession, model_type: str):
    if model_type in ACTIVE_MODELS:
        return ACTIVE_MODELS[model_type]
    version = await db.scalar(select(ModelVersion).where(ModelVersion.model_type == model_type, ModelVersion.is_active.is_(True)))
    if not version or not Path(version.file_path).exists():
        return None
    try:
        model = joblib.load(version.file_path)
        ACTIVE_MODELS[model_type] = model
        return model
    except (OSError, ValueError, EOFError):
        return None


async def demand_estimate(db: AsyncSession, product: Product, store: Store, inventory: Inventory | None, hour: int, dow: int, promotion: bool = False) -> tuple[float, str]:
    item_stock = inventory.reported_quantity if inventory else 0
    row = [product.id, store.id, hour, dow, datetime.utcnow().month, int(dow >= 5), int(promotion), item_stock]
    model = await active_model(db, "DEMAND")
    if model is not None:
        try:
            estimate = float(model.predict(np.asarray([row], dtype=float))[0])
            return max(0.2, round(estimate, 1)), "active model"
        except (ValueError, AttributeError):
            pass
    category_factor = 1.55 if product.category in ("Grocery", "Beverages", "Snacks", "Fruits", "Vegetables") else 0.78
    hour_factor = 1.45 if hour in (8, 9, 12, 18, 19, 20) else (0.48 if hour < 7 or hour > 22 else 0.82)
    day_factor = 1.22 if dow >= 5 else 1.0
    current_rows = await db.scalar(select(func.count(HistoricalOrder.id)).where(
        HistoricalOrder.product_id == product.id, HistoricalOrder.store_id == store.id,
        HistoricalOrder.hour == hour,
    ))
    # A smoothed rate from observed simulated orders plus hour/category seasonality.
    estimate = category_factor * hour_factor * day_factor * (0.9 + min(1.6, (current_rows or 0) / 12))
    if promotion:
        estimate *= 1.18
    return round(max(0.3, min(18.0, estimate)), 1), "seasonal baseline"


async def availability_estimate(
    db: AsyncSession, product: Product, store: Store, inventory: Inventory | None, quantity: int,
    hour: int | None = None, dow: int | None = None, demand: float | None = None,
) -> tuple[float, dict[str, Any]]:
    now = datetime.utcnow()
    hour, dow = hour if hour is not None else now.hour, dow if dow is not None else now.weekday()
    available = max(0, inventory.reported_quantity - inventory.reserved_quantity) if inventory else 0
    accuracy = inventory.inventory_accuracy if inventory else 0.72
    age_hours = max(0.0, (now - inventory.last_updated).total_seconds() / 3600) if inventory else 24.0
    forecast = demand if demand is not None else (await demand_estimate(db, product, store, inventory, hour, dow))[0]
    features = [available, quantity, accuracy, age_hours, max(0.3, forecast), hour, dow, store.id, product.id]
    model = await active_model(db, "AVAILABILITY")
    if model is not None:
        try:
            probability = float(model.predict_proba(np.asarray([features], dtype=float))[0][1])
            source = "active model"
        except (ValueError, AttributeError, IndexError):
            model = None
    if model is None:
        # A transparent baseline combines stock sufficiency, inventory accuracy,
        # freshness, and near-term demand exposure.
        gap = available - quantity - forecast * 0.55
        stock_confidence = logistic(gap * 0.34)
        freshness = math.exp(-age_hours / 20)
        reliability = 0.62 * accuracy + 0.20 * freshness + 0.18 * min(1.0, available / max(1.0, forecast * 1.5))
        probability = 0.72 * stock_confidence + 0.28 * reliability
        probability = 0.02 + 0.96 * probability if available >= quantity else 0.32 * probability
        source = "availability baseline"
    probability = min(0.995, max(0.01, probability))
    return probability, {
        "reported_quantity": inventory.reported_quantity if inventory else 0,
        "available_quantity": available, "inventory_accuracy": round(accuracy, 2),
        "inventory_age_minutes": round(age_hours * 60), "predicted_demand": forecast,
        "model_version": source,
    }


async def fulfillment_candidate(
    db: AsyncSession, product: Product, store: Store, inv: Inventory | None,
    quantity: int, distance: float, weights: dict[str, int] | None = None,
) -> dict[str, Any]:
    demand, demand_model = await demand_estimate(db, product, store, inv, datetime.utcnow().hour, datetime.utcnow().weekday())
    probability, details = await availability_estimate(db, product, store, inv, quantity, demand=demand)
    available = details["available_quantity"]
    adequacy = min(100.0, 100 * available / max(quantity + demand, 1))
    distance_score = max(0.0, 100 * (1 - distance / 18))
    future = max(0.0, min(100.0, 100 * logistic((available - quantity - demand) * 0.34)))
    sla = max(20.0, 100 - distance * 5.5)
    components = {
        "availability_confidence": round(probability * 100, 1), "inventory_adequacy": round(adequacy, 1),
        "distance": round(distance_score, 1), "future_availability": round(future, 1), "delivery_sla": round(sla, 1),
    }
    weights = weights or DEFAULT_SCORE_WEIGHTS
    score = sum(components[key] * weights[name] / 100 for key, name in (
        ("availability_confidence", "availability"), ("inventory_adequacy", "inventory"),
        ("distance", "distance"), ("future_availability", "future_availability"),
        ("delivery_sla", "delivery_sla"),
    ))
    reasons = [
        f"{components['availability_confidence']:.0f}% availability confidence",
        "Sufficient inventory" if available >= quantity else "Requested quantity exceeds available stock",
        "Low future stock risk" if future >= 65 else "Elevated future stock risk",
        f"{distance:.1f} km estimated distance",
        "Meets delivery window estimate" if distance <= 8 else "Longer estimated delivery distance",
    ]
    return {
        **store_payload(store), "distance_km": round(distance, 1), "availability_confidence": round(probability, 3),
        "confidence_percentage": round(probability * 100), "fulfillment_score": round(score),
        "predicted_demand": demand, "inventory": details, "score_components": components,
        "reasons": reasons, "expected_delivery": "25–40 min" if distance <= 5 else "35–55 min",
        "score_weights": weights,
        "prediction_source": details["model_version"], "demand_model": demand_model,
    }


async def current_inventory(db: AsyncSession, store_id: int, product_id: int) -> Inventory | None:
    return await db.scalar(select(Inventory).where(Inventory.store_id == store_id, Inventory.product_id == product_id))


def inventory_payload(inv: Inventory, product: Product, store: Store | None = None) -> dict[str, Any]:
    return {
        "id": inv.id, "store_id": inv.store_id, "store_name": store.name if store else None,
        "product_id": inv.product_id, "product_name": product.name, "sku": product.sku, "category": product.category,
        "reported_quantity": inv.reported_quantity, "reserved_quantity": inv.reserved_quantity,
        "available_quantity": max(0, inv.reported_quantity - inv.reserved_quantity),
        "last_updated": inv.last_updated.isoformat(), "reorder_level": inv.reorder_level,
        "safety_stock": inv.safety_stock, "inventory_accuracy": inv.inventory_accuracy,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "FulfillIQ API"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterInput, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email or len(email) > 255:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, hashed_password=get_password_hash(payload.password), role=payload.role, store_id=payload.store_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id, user.role.value, user.store_id)
    return {"access_token": token, "token_type": "bearer", "user": user_payload(user)}


@app.post("/auth/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.", headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token(user.id, user.role.value, user.store_id)
    return {"access_token": token, "token_type": "bearer", "user": user_payload(user)}


@app.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return user_payload(user)


@app.get("/products")
async def list_products(
    search: str | None = None, category: str | None = None, limit: int = Query(48, ge=1, le=200),
    offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Product.name.ilike(term), Product.category.ilike(term), Product.brand.ilike(term), Product.sku.ilike(term)))
    if category:
        query = query.where(Product.category == category)
    products = (await db.scalars(query.order_by(Product.id).offset(offset).limit(limit))).all()
    count_query = select(func.count(Product.id)).where(Product.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        count_query = count_query.where(or_(Product.name.ilike(term), Product.category.ilike(term), Product.brand.ilike(term), Product.sku.ilike(term)))
    if category:
        count_query = count_query.where(Product.category == category)
    return {"items": [product_payload(p) for p in products], "total": await db.scalar(count_query) or 0}


@app.get("/products/search")
async def search_products(q: str = Query(min_length=1), db: AsyncSession = Depends(get_db)):
    term = f"%{q.strip()}%"
    products = (await db.scalars(select(Product).where(Product.is_active.is_(True), or_(Product.name.ilike(term), Product.category.ilike(term))).limit(30))).all()
    return [product_payload(p) for p in products]


@app.get("/products/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product_payload(product)


@app.get("/stores")
async def list_stores(db: AsyncSession = Depends(get_db)):
    stores = (await db.scalars(select(Store).where(Store.is_active.is_(True)).order_by(Store.id))).all()
    return [store_payload(store) for store in stores]


@app.get("/stores/nearby")
async def nearby_stores(
    latitude: float, longitude: float, radius_km: float = Query(12, ge=1, le=80), db: AsyncSession = Depends(get_db),
):
    stores = (await db.scalars(select(Store).where(Store.is_active.is_(True)))).all()
    nearby = [{**store_payload(s), "distance_km": round(haversine_km(latitude, longitude, s.latitude, s.longitude), 1)} for s in stores]
    return sorted([s for s in nearby if s["distance_km"] <= radius_km], key=lambda x: x["distance_km"])


@app.get("/stores/{store_id}")
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    return store_payload(store)


@app.get("/inventory")
async def all_inventory(
    store_id: int | None = None, search: str | None = None, limit: int = Query(500, ge=1, le=2000),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if user.role == RoleEnum.CUSTOMER:
        raise HTTPException(status_code=403, detail="Inventory is available to store teams and platform admins.")
    if user.role == RoleEnum.STORE_MANAGER:
        store_id = user.store_id
    stmt = select(Inventory, Product, Store).join(Product).join(Store)
    if store_id:
        stmt = stmt.where(Inventory.store_id == store_id)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    rows = (await db.execute(stmt.order_by(Inventory.reported_quantity).limit(limit))).all()
    return [inventory_payload(inv, product, store) for inv, product, store in rows]


@app.get("/stores/{store_id}/inventory")
async def store_inventory(store_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_store_access(user, store_id)
    if user.role == RoleEnum.CUSTOMER:
        raise HTTPException(status_code=403, detail="Store inventory is not available to customers.")
    rows = (await db.execute(select(Inventory, Product, Store).join(Product).join(Store).where(Inventory.store_id == store_id).order_by(Product.name))).all()
    return [inventory_payload(inv, product, store) for inv, product, store in rows]


@app.patch("/inventory/{inventory_id}")
async def patch_inventory(
    inventory_id: int, payload: InventoryUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    inv = await db.get(Inventory, inventory_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found.")
    if user.role not in (RoleEnum.PLATFORM_ADMIN, RoleEnum.STORE_MANAGER):
        raise HTTPException(status_code=403, detail="Inventory updates are limited to store teams and admins.")
    require_store_access(user, inv.store_id)
    delta = payload.reported_quantity - inv.reported_quantity
    inv.reported_quantity = payload.reported_quantity
    inv.last_updated = datetime.utcnow()
    db.add(InventoryEvent(store_id=inv.store_id, product_id=inv.product_id, event_type="inventory_correction", source="ERP", quantity_delta=delta, note=payload.note))
    await db.commit()
    return {"ok": True, "reported_quantity": inv.reported_quantity}


@app.post("/predict/demand")
async def predict_demand(payload: DemandInput, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    product, store = await db.get(Product, payload.product_id), await db.get(Store, payload.store_id)
    if not product or not store:
        raise HTTPException(status_code=404, detail="Product or store not found.")
    if user.role == RoleEnum.STORE_MANAGER:
        require_store_access(user, store.id)
    inv = await current_inventory(db, store.id, product.id)
    estimate, source = await demand_estimate(db, product, store, inv, payload.hour, payload.day_of_week, payload.promotion_flag)
    prediction = DemandPrediction(
        product_id=product.id, store_id=store.id, predicted_for=datetime.utcnow().replace(hour=payload.hour, minute=0, second=0, microsecond=0),
        predicted_demand=estimate, lower_bound=max(0, round(estimate * 0.65, 1)), upper_bound=round(estimate * 1.4 + 1, 1), model_version=source,
    )
    db.add(prediction)
    await db.commit()
    return {"product": product.name, "store": store.name, "hour": payload.hour, "day_of_week": payload.day_of_week,
            "predicted_demand": estimate, "lower_bound": prediction.lower_bound, "upper_bound": prediction.upper_bound,
            "model_version": source, "prediction_timestamp": datetime.utcnow().isoformat()}


@app.post("/predict/availability")
async def predict_availability(payload: AvailabilityInput, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    product, store = await db.get(Product, payload.product_id), await db.get(Store, payload.store_id)
    if not product or not store:
        raise HTTPException(status_code=404, detail="Product or store not found.")
    if user.role == RoleEnum.STORE_MANAGER:
        require_store_access(user, store.id)
    inv = await current_inventory(db, store.id, product.id)
    probability, details = await availability_estimate(db, product, store, inv, payload.quantity)
    db.add(AvailabilityPrediction(product_id=product.id, store_id=store.id, requested_quantity=payload.quantity,
                                  availability_probability=probability, reported_quantity=details["reported_quantity"]))
    await db.commit()
    return {"availability_probability": round(probability, 3), "confidence_percentage": round(probability * 100),
            "reported_inventory": details["reported_quantity"], "details": details}


@app.post("/recommend/store")
async def recommend_store(payload: RecommendationInput, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    stores = (await db.scalars(select(Store).where(Store.is_active.is_(True)))).all()
    weights = await fulfillment_weights(db)
    candidates = []
    for store in stores:
        distance = haversine_km(payload.customer_lat, payload.customer_lng, store.latitude, store.longitude)
        if distance > payload.radius_km:
            continue
        inventory = await current_inventory(db, store.id, product.id)
        if inventory is None:
            continue
        candidates.append(await fulfillment_candidate(db, product, store, inventory, payload.quantity, distance, weights))
    if not candidates:
        raise HTTPException(status_code=404, detail="No nearby stores carry this item. Try a wider search radius.")
    candidates.sort(key=lambda item: (-item["fulfillment_score"], -item["availability_confidence"], item["distance_km"]))
    # Persist the prediction snapshots for platform evaluation and audit.
    for item in candidates:
        db.add(AvailabilityPrediction(product_id=product.id, store_id=item["id"], requested_quantity=payload.quantity,
                                      availability_probability=item["availability_confidence"], reported_quantity=item["inventory"]["reported_quantity"]))
    await db.commit()
    return {"product": product_payload(product), "requested_quantity": payload.quantity,
            "estimated_geographic_distance": True, "recommended_store": candidates[0], "alternatives": candidates[1:5],
            "weights": weights}


def order_payload(order: Order) -> dict[str, Any]:
    return {
        "id": order.id, "store_id": order.store_id, "store_name": order.store.name if order.store else None,
        "timestamp": order.timestamp.isoformat(), "status": order.status, "total_amount": round(order.total_amount, 2),
        "items": [{"product_id": line.product_id, "product_name": line.product.name if line.product else "Item",
                    "quantity": line.quantity, "price": line.price_at_time} for line in order.items],
        "customer_lat": order.customer_lat, "customer_lng": order.customer_lng,
    }


@app.post("/orders", status_code=201)
async def create_order(payload: OrderInput, user: User = Depends(require_roles(RoleEnum.CUSTOMER)), db: AsyncSession = Depends(get_db)):
    store = await db.get(Store, payload.store_id)
    if not store or not store.is_active:
        raise HTTPException(status_code=404, detail="Selected store is not available.")
    prices, inventory_rows, total = [], [], 0.0
    for line in payload.items:
        product = await db.get(Product, line.product_id)
        inv = await current_inventory(db, store.id, line.product_id)
        available = max(0, inv.reported_quantity - inv.reserved_quantity) if inv else 0
        probability = (await availability_estimate(db, product, store, inv, line.quantity))[0] if product else 0
        if not product or not inv or available < line.quantity or probability < 0.25:
            raise HTTPException(status_code=409, detail=f"{product.name if product else 'Item'} is no longer available in the selected quantity at this store.")
        inventory_rows.append((inv, line.quantity))
        prices.append((product, line.quantity))
        total += product.price * line.quantity
    order = Order(customer_id=user.id, store_id=store.id, customer_lat=payload.customer_lat, customer_lng=payload.customer_lng,
                  status="CONFIRMED", total_amount=total)
    for product, quantity in prices:
        order.items.append(OrderItem(product_id=product.id, quantity=quantity, price_at_time=product.price))
    db.add(order)
    await db.flush()
    for inv, quantity in inventory_rows:
        inv.reported_quantity -= quantity
        inv.last_updated = datetime.utcnow()
        db.add(InventoryEvent(store_id=store.id, product_id=inv.product_id, event_type="sale", source="POS", quantity_delta=-quantity, note=f"Order #{order.id}"))
    await db.commit()
    order = await db.scalar(select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.store)).where(Order.id == order.id))
    return order_payload(order)


@app.get("/orders")
async def list_orders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.store)).order_by(Order.timestamp.desc()).limit(100)
    if user.role == RoleEnum.CUSTOMER:
        stmt = stmt.where(Order.customer_id == user.id)
    elif user.role == RoleEnum.STORE_MANAGER:
        stmt = stmt.where(Order.store_id == user.store_id)
    orders = (await db.scalars(stmt)).all()
    return [order_payload(order) for order in orders]


@app.get("/orders/{order_id}")
async def get_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await db.scalar(select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.store)).where(Order.id == order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if user.role == RoleEnum.CUSTOMER and order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="This order belongs to another customer.")
    if user.role == RoleEnum.STORE_MANAGER:
        require_store_access(user, order.store_id)
    return order_payload(order)


@app.get("/store/dashboard")
async def store_dashboard(user: User = Depends(require_roles(RoleEnum.STORE_MANAGER)), db: AsyncSession = Depends(get_db)):
    store_id = user.store_id
    if not store_id:
        raise HTTPException(status_code=403, detail="Your account is not assigned to a store.")
    store = await db.get(Store, store_id)
    inv_count = await db.scalar(select(func.count(Inventory.id)).where(Inventory.store_id == store_id)) or 0
    low_count = await db.scalar(select(func.count(Inventory.id)).where(Inventory.store_id == store_id, Inventory.reported_quantity <= Inventory.reorder_level)) or 0
    active_orders = await db.scalar(select(func.count(Order.id)).where(Order.store_id == store_id, Order.status.in_(["CONFIRMED", "PREPARING", "OUT_FOR_DELIVERY"]))) or 0
    return {"store": store_payload(store), "inventory_items": inv_count, "low_stock_items": low_count,
            "active_orders": active_orders, "simulated_city": "Coimbatore"}


@app.get("/store/orders")
async def store_orders(user: User = Depends(require_roles(RoleEnum.STORE_MANAGER)), db: AsyncSession = Depends(get_db)):
    orders = (await db.scalars(select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.store)).where(Order.store_id == user.store_id).order_by(Order.timestamp.desc()).limit(100))).all()
    return [order_payload(o) for o in orders]


async def store_risk_rows(db: AsyncSession, store_id: int, limit: int = 60):
    rows = (await db.execute(select(Inventory, Product).join(Product).where(Inventory.store_id == store_id).order_by(Inventory.reported_quantity))).all()
    risk = []
    store = await db.get(Store, store_id)
    for inv, product in rows[:limit]:
        demand, _ = await demand_estimate(db, product, store, inv, datetime.utcnow().hour, datetime.utcnow().weekday())
        short = max(0, math.ceil(demand + inv.safety_stock - inv.reported_quantity + inv.reserved_quantity))
        risk.append({**inventory_payload(inv, product), "predicted_demand": demand,
                     "risk": "HIGH" if short > 0 else ("MEDIUM" if inv.reported_quantity <= inv.reorder_level else "LOW"),
                     "projected_shortage": short})
    return risk


@app.get("/store/alerts")
async def store_alerts(user: User = Depends(require_roles(RoleEnum.STORE_MANAGER)), db: AsyncSession = Depends(get_db)):
    rows = await store_risk_rows(db, user.store_id)
    return sorted([r for r in rows if r["risk"] != "LOW"], key=lambda r: (-r["projected_shortage"], r["reported_quantity"]))[:30]


def recommendation_payload(rec: Recommendation, store: Store | None = None, product: Product | None = None) -> dict[str, Any]:
    return {"id": rec.id, "store_id": rec.store_id, "store_name": store.name if store else (rec.store.name if rec.store else None),
            "product_id": rec.product_id, "product_name": product.name if product else (rec.product.name if rec.product else None),
            "action_type": rec.action_type, "recommended_quantity": rec.recommended_quantity,
            "deadline": rec.deadline.isoformat() if rec.deadline else None, "reason": rec.reason, "status": rec.status}


@app.get("/store/recommendations")
async def store_recommendations(user: User = Depends(require_roles(RoleEnum.STORE_MANAGER)), db: AsyncSession = Depends(get_db)):
    recs = (await db.scalars(select(Recommendation).options(selectinload(Recommendation.store), selectinload(Recommendation.product)).where(Recommendation.store_id == user.store_id).order_by(Recommendation.status, Recommendation.deadline))).all()
    if not recs:
        alerts = await store_alerts(user, db)
        for alert in alerts[:10]:
            if alert["projected_shortage"] <= 0:
                continue
            rec = Recommendation(
                store_id=user.store_id, product_id=alert["product_id"], action_type="REPLENISHMENT",
                recommended_quantity=alert["projected_shortage"], deadline=datetime.utcnow() + timedelta(hours=1),
                reason=f"Predicted demand of {alert['predicted_demand']} units plus safety stock exceeds available inventory.",
                status="PENDING",
            )
            db.add(rec)
            recs.append(rec)
        await db.flush()
        await db.commit()
        for rec in recs:
            rec.product = await db.get(Product, rec.product_id)
            rec.store = await db.get(Store, rec.store_id)
    return [recommendation_payload(r) for r in recs]


@app.post("/store/recommendations/{recommendation_id}/acknowledge")
async def acknowledge_recommendation(recommendation_id: int, user: User = Depends(require_roles(RoleEnum.STORE_MANAGER)), db: AsyncSession = Depends(get_db)):
    rec = await db.get(Recommendation, recommendation_id)
    if not rec or rec.store_id != user.store_id:
        raise HTTPException(status_code=404, detail="Recommendation not found for this store.")
    rec.status = "ACKNOWLEDGED"
    await db.commit()
    return {"ok": True, "status": rec.status}


@app.post("/store/recommendations/{recommendation_id}/complete")
async def complete_recommendation(recommendation_id: int, user: User = Depends(require_roles(RoleEnum.STORE_MANAGER)), db: AsyncSession = Depends(get_db)):
    rec = await db.get(Recommendation, recommendation_id)
    if not rec or rec.store_id != user.store_id:
        raise HTTPException(status_code=404, detail="Recommendation not found for this store.")
    inv = await current_inventory(db, rec.store_id, rec.product_id)
    if not inv:
        inv = Inventory(store_id=rec.store_id, product_id=rec.product_id, reported_quantity=0)
        db.add(inv)
        await db.flush()
    inv.reported_quantity += rec.recommended_quantity
    inv.last_updated = datetime.utcnow()
    rec.status = "COMPLETED"
    db.add(InventoryEvent(store_id=rec.store_id, product_id=rec.product_id, event_type="replenishment", source="WMS", quantity_delta=rec.recommended_quantity, note=f"FulfillIQ recommendation #{rec.id} completed"))
    await db.commit()
    return {"ok": True, "status": rec.status, "reported_quantity": inv.reported_quantity}


@app.get("/admin/analytics")
async def admin_analytics(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    stores = await db.scalar(select(func.count(Store.id)).where(Store.is_active.is_(True))) or 0
    warehouses = await db.scalar(select(func.count(Store.id)).where(Store.type == StoreTypeEnum.WAREHOUSE)) or 0
    products = await db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0
    live_orders = await db.scalar(select(func.count(Order.id))) or 0
    stockout_count = await db.scalar(select(func.count(HistoricalOrder.id)).where(HistoricalOrder.stockout.is_(True))) or 0
    historical_count = await db.scalar(select(func.count(HistoricalOrder.id))) or 0
    predictions_count = await db.scalar(select(func.count(AvailabilityPrediction.id))) or 0
    avg_confidence = await db.scalar(select(func.avg(AvailabilityPrediction.availability_probability))) if predictions_count else None
    inventory_count = await db.scalar(select(func.count(Inventory.id))) or 0
    low_stock = await db.scalar(select(func.count(Inventory.id)).where(Inventory.reported_quantity <= Inventory.reorder_level)) or 0
    demand_version = await db.scalar(select(ModelVersion.version_name).where(ModelVersion.model_type == "DEMAND", ModelVersion.is_active.is_(True)))
    availability_version = await db.scalar(select(ModelVersion.version_name).where(ModelVersion.model_type == "AVAILABILITY", ModelVersion.is_active.is_(True)))
    hourly_rows = (await db.execute(
        select(HistoricalOrder.hour, func.sum(HistoricalOrder.quantity))
        .group_by(HistoricalOrder.hour).order_by(HistoricalOrder.hour)
    )).all()
    hourly_map = {int(hour): int(units or 0) for hour, units in hourly_rows}
    category_rows = (await db.execute(
        select(Product.category, func.sum(HistoricalOrder.quantity))
        .join(HistoricalOrder, HistoricalOrder.product_id == Product.id)
        .group_by(Product.category).order_by(func.sum(HistoricalOrder.quantity).desc())
    )).all()
    health_counts = {"HEALTHY": 0, "MEDIUM": 0, "HIGH": 0}
    health_rows = (await db.execute(
        select(Inventory.store_id, func.count(Inventory.id),
               func.sum(__import__("sqlalchemy").case((Inventory.reported_quantity <= Inventory.reorder_level, 1), else_=0)))
        .group_by(Inventory.store_id)
    )).all()
    for _, total, risk_count in health_rows:
        ratio = (risk_count or 0) / max(1, total or 0)
        health_counts["HIGH" if ratio > 0.32 else "MEDIUM" if ratio > 0.19 else "HEALTHY"] += 1
    return {
        "stores": stores, "warehouses": warehouses, "products": products, "active_orders": live_orders,
        "high_risk_items": low_stock, "inventory_records": inventory_count, "historical_orders": historical_count,
        "predicted_shortages": low_stock, "average_availability_confidence": round((avg_confidence or 0) * 100, 1),
        "stockout_rate": round(stockout_count / historical_count * 100, 1) if historical_count else 0,
        "fulfillment_success_rate": round((await db.scalar(select(func.avg(func.cast(HistoricalOrder.fulfilled, __import__("sqlalchemy").Integer)))) or 0) * 100, 1),
        "demand_model": demand_version or "Seasonal baseline", "availability_model": availability_version or "Availability baseline",
        "prediction_count": predictions_count, "generated_at": datetime.utcnow().isoformat(),
        "hourly_demand": [{"hour": hour, "units": hourly_map.get(hour, 0)} for hour in range(24)],
        "category_mix": [{"category": category, "units": int(units or 0)} for category, units in category_rows],
        "store_health": [{"risk": key, "count": value} for key, value in health_counts.items()],
    }


@app.get("/admin/map")
async def admin_map(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    stores = (await db.scalars(select(Store).where(Store.is_active.is_(True)).order_by(Store.id))).all()
    result = []
    for store in stores:
        total = await db.scalar(select(func.count(Inventory.id)).where(Inventory.store_id == store.id)) or 0
        high = await db.scalar(select(func.count(Inventory.id)).where(Inventory.store_id == store.id, Inventory.reported_quantity <= Inventory.reorder_level)) or 0
        order_count = await db.scalar(select(func.count(Order.id)).where(Order.store_id == store.id, Order.status.in_(["CONFIRMED", "PREPARING", "OUT_FOR_DELIVERY"]))) or 0
        risk_pct = high / total if total else 0
        result.append({**store_payload(store), "inventory_health": round((1 - risk_pct) * 100),
                       "risk": "HIGH" if risk_pct > 0.32 else ("MEDIUM" if risk_pct > 0.19 else "HEALTHY"),
                       "active_orders": order_count, "at_risk_items": high})
    return result


@app.get("/admin/orders")
async def admin_orders(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    orders = (await db.scalars(select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.store)).order_by(Order.timestamp.desc()).limit(200))).all()
    return [order_payload(o) for o in orders]


@app.get("/admin/predictions")
async def admin_predictions(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    demands = (await db.execute(select(DemandPrediction, Product, Store).join(Product).join(Store).order_by(DemandPrediction.created_at.desc()).limit(100))).all()
    availability = (await db.execute(select(AvailabilityPrediction, Product, Store).join(Product).join(Store).order_by(AvailabilityPrediction.created_at.desc()).limit(100))).all()
    return {
        "demand": [{"product": p.name, "store": s.name, "predicted_for": d.predicted_for.isoformat() if d.predicted_for else None,
                    "predicted_demand": d.predicted_demand, "lower_bound": d.lower_bound, "upper_bound": d.upper_bound, "model_version": d.model_version} for d, p, s in demands],
        "availability": [{"product": p.name, "store": s.name, "availability_probability": a.availability_probability,
                           "confidence_percentage": round(a.availability_probability * 100), "requested_quantity": a.requested_quantity,
                           "reported_quantity": a.reported_quantity, "created_at": a.created_at.isoformat()} for a, p, s in availability],
    }


@app.get("/admin/models")
async def admin_models(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    models = (await db.scalars(select(ModelVersion).order_by(ModelVersion.training_timestamp.desc()))).all()
    return [{"id": m.id, "model_type": m.model_type, "version_name": m.version_name, "dataset_size": m.dataset_size,
             "training_timestamp": m.training_timestamp.isoformat(), "is_active": m.is_active,
             "metrics": json.loads(m.metrics or "{}"), "features": json.loads(m.features or "[]"),
             "hyperparameters": json.loads(m.hyperparameters or "{}") } for m in models]


@app.get("/admin/settings/fulfillment")
async def get_fulfillment_settings(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    return {"weights": await fulfillment_weights(db), "note": "Prototype defaults; weights must total 100."}


@app.put("/admin/settings/fulfillment")
async def update_fulfillment_settings(
    payload: FulfillmentWeightInput, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    weights = payload.model_dump()
    if sum(weights.values()) != 100:
        raise HTTPException(status_code=422, detail="Fulfillment score weights must total 100.")
    state = await db.get(SimulationState, 1)
    if not state:
        state = SimulationState(id=1, simulated_at=datetime.utcnow(), seed=settings.SEED, is_running=False)
        db.add(state)
    state.fulfillment_weights = json.dumps(weights)
    await db.commit()
    return {"weights": weights, "note": "Updated prototype score weights."}


async def train_model(db: AsyncSession, model_type: str, sample_fraction: float = 1.0) -> dict[str, Any]:
    count = await db.scalar(select(func.count(HistoricalOrder.id))) or 0
    if count < 100:
        raise HTTPException(status_code=400, detail="Generate at least 100 historical examples before training.")
    records = (await db.execute(select(HistoricalOrder).order_by(HistoricalOrder.id))).scalars().all()
    rng = np.random.default_rng(settings.SEED)
    if sample_fraction < 1 and len(records) > 0:
        size = max(100, int(len(records) * sample_fraction))
        indexes = rng.choice(len(records), size=min(size, len(records)), replace=False)
        records = [records[int(i)] for i in indexes]
    if model_type == "DEMAND":
        features = DEMAND_FEATURES
        x = np.asarray([[getattr(r, name) if getattr(r, name) is not None else 0 for name in features] for r in records], dtype=float)
        y = np.asarray([r.quantity for r in records], dtype=float)
        model = RandomForestRegressor(n_estimators=70, max_depth=15, min_samples_leaf=3, random_state=42, n_jobs=-1)
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        metrics = {"mae": round(float(mean_absolute_error(y_test, pred)), 3), "rmse": round(float(mean_squared_error(y_test, pred) ** 0.5), 3),
                   "r2": round(float(r2_score(y_test, pred)), 3)}
    else:
        features = AVAILABILITY_FEATURES
        x = np.asarray([[
            r.inventory_before_order or 0, r.quantity or 1, r.inventory_accuracy or 0.8,
            r.inventory_age_hours or 0, r.sales_velocity or 1, r.hour or 0,
            r.day_of_week or 0, r.store_id or 0, r.product_id or 0,
        ] for r in records], dtype=float)
        y = np.asarray([int(bool(r.fulfilled)) for r in records], dtype=int)
        model = RandomForestClassifier(n_estimators=70, max_depth=15, min_samples_leaf=3, class_weight="balanced", random_state=42, n_jobs=-1)
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        proba = model.predict_proba(x_test)[:, 1]
        metrics = {"accuracy": round(float(accuracy_score(y_test, pred)), 3),
                   "precision": round(float(precision_score(y_test, pred, zero_division=0)), 3),
                   "recall": round(float(recall_score(y_test, pred, zero_division=0)), 3),
                   "f1": round(float(f1_score(y_test, pred, zero_division=0)), 3),
                   "roc_auc": round(float(roc_auc_score(y_test, proba)), 3) if len(np.unique(y_test)) > 1 else None}
    storage = Path(settings.MODEL_STORAGE_PATH)
    storage.mkdir(parents=True, exist_ok=True)
    latest = await db.scalar(select(func.count(ModelVersion.id)).where(ModelVersion.model_type == model_type)) or 0
    version_name = f"{model_type.lower()}_v{latest + 1}"
    file_path = str(storage / f"{version_name}.joblib")
    joblib.dump(model, file_path)
    version = ModelVersion(model_type=model_type, version_name=version_name, file_path=file_path, dataset_size=len(records),
                           is_active=False, metrics=json.dumps(metrics), features=json.dumps(features),
                           hyperparameters=json.dumps(model.get_params()))
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return {"id": version.id, "model_type": model_type, "version_name": version_name,
            "dataset_size": len(records), "training_timestamp": version.training_timestamp.isoformat(),
            "metrics": metrics, "features": features, "hyperparameters": json.loads(version.hyperparameters)}


@app.post("/admin/models/demand/train")
async def train_demand(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    ACTIVE_MODELS.pop("DEMAND", None)
    return await train_model(db, "DEMAND")


@app.post("/admin/models/availability/train")
async def train_availability(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    ACTIVE_MODELS.pop("AVAILABILITY", None)
    return await train_model(db, "AVAILABILITY")


@app.post("/admin/models/{model_id}/activate")
async def activate_model(model_id: int, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    version = await db.get(ModelVersion, model_id)
    if not version or not Path(version.file_path).exists():
        raise HTTPException(status_code=404, detail="Trained model file not found.")
    models = (await db.scalars(select(ModelVersion).where(ModelVersion.model_type == version.model_type))).all()
    for model in models:
        model.is_active = model.id == version.id
    ACTIVE_MODELS[version.model_type] = joblib.load(version.file_path)
    await db.commit()
    return {"ok": True, "active_model": version.version_name}


@app.get("/admin/models/{model_id}/metrics")
async def model_metrics(model_id: int, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelVersion, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model version not found.")
    return {"id": model.id, "version_name": model.version_name, "model_type": model.model_type,
            "metrics": json.loads(model.metrics or "{}"), "dataset_size": model.dataset_size}

@app.get("/stores")
async def public_stores(db: AsyncSession = Depends(get_db)):
    return [store_payload(s) for s in (await db.scalars(select(Store).where(Store.is_active.is_(True)).order_by(Store.id))).all()]


@app.get("/admin/events")
async def admin_events(
    store_id: int | None = None, product_id: int | None = None, source: str | None = None,
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN, RoleEnum.STORE_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Multi-source inventory event ledger — POS, WMS, ERP, RFID."""
    query = select(InventoryEvent)
    if store_id:
        query = query.where(InventoryEvent.store_id == store_id)
    if product_id:
        query = query.where(InventoryEvent.product_id == product_id)
    if source:
        query = query.where(InventoryEvent.source == source.upper())
    events = (await db.scalars(query.order_by(InventoryEvent.created_at.desc()).offset(offset).limit(limit))).all()
    return [{
        "id": e.id, "store_id": e.store_id, "product_id": e.product_id,
        "event_type": e.event_type, "source": e.source, "quantity_delta": e.quantity_delta,
        "reported_quantity": e.reported_quantity, "note": e.note,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in events]


@app.get("/admin/reconciliation/{store_id}/{product_id}")
async def reconciliation_view(
    store_id: int, product_id: int,
    user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN, RoleEnum.STORE_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Per-SKU reconciliation: compare reported quantities across POS, WMS, ERP, RFID sources."""
    events = (await db.scalars(
        select(InventoryEvent)
        .where(InventoryEvent.store_id == store_id, InventoryEvent.product_id == product_id)
        .order_by(InventoryEvent.created_at.desc())
    )).all()
    inv = await db.scalar(
        select(Inventory).where(Inventory.store_id == store_id, Inventory.product_id == product_id)
    )
    source_summary: dict[str, Any] = {}
    for src in ("POS", "WMS", "ERP", "RFID"):
        src_events = [e for e in events if e.source == src]
        latest = src_events[0] if src_events else None
        source_summary[src] = {
            "event_count": len(src_events),
            "latest_reported_quantity": latest.reported_quantity if latest and latest.reported_quantity is not None else None,
            "latest_event_type": latest.event_type if latest else None,
            "latest_timestamp": latest.created_at.isoformat() if latest and latest.created_at else None,
        }
    reported_values = [v["latest_reported_quantity"] for v in source_summary.values() if v["latest_reported_quantity"] is not None]
    discrepancy = (max(reported_values) - min(reported_values)) if len(reported_values) >= 2 else 0
    confidence = round(max(0.0, min(1.0, 1.0 - discrepancy * 0.08)), 2) if reported_values else 0.0
    return {
        "store_id": store_id, "product_id": product_id,
        "current_reported_quantity": inv.reported_quantity if inv else None,
        "inventory_accuracy": inv.inventory_accuracy if inv else None,
        "sources": source_summary,
        "discrepancy_spread": discrepancy,
        "estimated_confidence": confidence,
        "total_events": len(events),
        "recommendation": "VERIFY_IMMEDIATELY" if discrepancy >= 5 else ("MONITOR" if discrepancy >= 2 else "TRUSTED"),
    }


@app.get("/admin/source-summary")
async def source_summary(
    user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Network-wide event source distribution summary."""
    result = await db.execute(
        select(InventoryEvent.source, InventoryEvent.event_type, func.count(InventoryEvent.id))
        .group_by(InventoryEvent.source, InventoryEvent.event_type)
        .order_by(InventoryEvent.source)
    )
    rows = result.all()
    summary: dict[str, Any] = {}
    for source_name, event_type, count in rows:
        if source_name not in summary:
            summary[source_name] = {"total": 0, "event_types": {}}
        summary[source_name]["total"] += count
        summary[source_name]["event_types"][event_type] = count
    return summary


@app.get("/admin/stores")
async def admin_stores(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    return [store_payload(s) for s in (await db.scalars(select(Store).order_by(Store.id))).all()]


@app.post("/admin/stores", status_code=201)
async def create_store(payload: StoreCreate, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    store = Store(**payload.model_dump(), operating_hours="7:00 AM – 11:00 PM", is_active=True)
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store_payload(store)


@app.get("/admin/products")
async def admin_products(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    return {"items": [product_payload(p) for p in (await db.scalars(select(Product).order_by(Product.id).limit(1000))).all()],
            "total": await db.scalar(select(func.count(Product.id))) or 0}


@app.post("/admin/products", status_code=201)
async def create_product(payload: ProductCreate, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    product = Product(**payload.model_dump(), image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=480&h=360&fit=crop", is_active=True)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product_payload(product)


@app.post("/admin/data/generate")
async def generate_data(payload: GenerateInput, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    current = await db.scalar(select(func.count(HistoricalOrder.id))) or 0
    amount = max(0, payload.historical_orders - current)
    state = await db.get(SimulationState, 1)
    if state:
        state.seed = payload.seed
    added = await generate_historical_data(db, amount, payload.seed) if amount else 0
    return {"stores": await db.scalar(select(func.count(Store.id))) or 0,
            "products": await db.scalar(select(func.count(Product.id))) or 0,
            "historical_orders": current + added, "records_added": added, "seed": payload.seed}


@app.get("/admin/simulation/state")
async def simulation_state(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    state = await db.get(SimulationState, 1)
    return {"simulated_at": state.simulated_at.isoformat(), "seed": state.seed, "is_running": state.is_running} if state else {"simulated_at": datetime.utcnow().isoformat(), "seed": settings.SEED, "is_running": False}


@app.post("/admin/simulation/step")
async def simulation_step(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    state = await db.get(SimulationState, 1)
    if not state:
        state = SimulationState(id=1, simulated_at=datetime.utcnow(), seed=settings.SEED)
        db.add(state)
    state.simulated_at += timedelta(hours=1)
    rng = random.Random(state.seed + int(state.simulated_at.timestamp()) // 3600)
    rows = (await db.scalars(select(Inventory).order_by(func.random()).limit(12))).all()
    changes = []
    for inv in rows:
        delta = min(inv.reported_quantity, rng.randint(0, 2))
        inv.reported_quantity -= delta
        inv.last_updated = datetime.utcnow()
        db.add(InventoryEvent(store_id=inv.store_id, product_id=inv.product_id, event_type="sale", source="POS", quantity_delta=-delta, note="One-hour simulation step"))
        changes.append({"store_id": inv.store_id, "product_id": inv.product_id, "units_sold": delta, "stock_after": inv.reported_quantity})
    transitions = []
    for current, following in (("CONFIRMED", "PREPARING"), ("PREPARING", "OUT_FOR_DELIVERY"), ("OUT_FOR_DELIVERY", "DELIVERED")):
        order = await db.scalar(select(Order).where(Order.status == current).order_by(Order.timestamp).limit(1))
        if order:
            order.status = following
            transitions.append({"order_id": order.id, "from": current, "to": following})
    await db.commit()
    return {"simulated_at": state.simulated_at.isoformat(), "changes": changes, "order_transitions": transitions}


@app.post("/admin/transfers", status_code=201)
async def transfer_stock(payload: TransferInput, user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    source = await current_inventory(db, payload.from_store_id, payload.product_id)
    target = await current_inventory(db, payload.to_store_id, payload.product_id)
    if not source or source.reported_quantity - source.reserved_quantity < payload.quantity:
        raise HTTPException(status_code=409, detail="Source store does not have enough available stock.")
    if not target:
        target = Inventory(store_id=payload.to_store_id, product_id=payload.product_id, reported_quantity=0)
        db.add(target)
        await db.flush()
    before = target.reported_quantity
    source.reported_quantity -= payload.quantity
    target.reported_quantity += payload.quantity
    source.last_updated = target.last_updated = datetime.utcnow()
    transfer = StoreTransfer(from_store_id=payload.from_store_id, to_store_id=payload.to_store_id, product_id=payload.product_id, quantity=payload.quantity, status="COMPLETED")
    db.add(transfer)
    db.add_all([
        InventoryEvent(store_id=payload.from_store_id, product_id=payload.product_id, event_type="transfer", source="ERP", quantity_delta=-payload.quantity, note=f"Transfer to Store {payload.to_store_id:03d}"),
        InventoryEvent(store_id=payload.to_store_id, product_id=payload.product_id, event_type="transfer", source="ERP", quantity_delta=payload.quantity, note=f"Transfer from Store {payload.from_store_id:03d}"),
    ])
    await db.commit()
    return {"transfer_id": transfer.id, "before": before, "transferred": payload.quantity, "after": target.reported_quantity}


@app.get("/admin/evaluation")
async def evaluation(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    """Compare nearest-store and fulfillment ranking on a deterministic historical slice."""
    records = (await db.scalars(select(HistoricalOrder).order_by(HistoricalOrder.id).limit(250))).all()
    stores = (await db.scalars(select(Store))).all()
    products = {p.id: p for p in (await db.scalars(select(Product))).all()}
    store_map = {s.id: s for s in stores}
    inventory_rows = (await db.scalars(select(Inventory))).all()
    inventory_map = {(inv.store_id, inv.product_id): inv for inv in inventory_rows}
    weights = await fulfillment_weights(db)
    if not records or not stores:
        return {"sample_size": 0, "baseline": {}, "fulfilliq": {}, "note": "Generate historical records to evaluate strategies."}
    # The held-out generated order's fulfillment outcome is applied to each strategy's
    # selected candidate using the recorded inventory context. No improvement is assumed.
    baseline_ok = fiq_ok = 0
    baseline_dist, fiq_dist = [], []
    for record in records:
        actual_store = store_map.get(record.store_id)
        if not actual_store:
            continue
        nearest = min(stores, key=lambda s: haversine_km(record.customer_lat, record.customer_lng, s.latitude, s.longitude))
        product = products.get(record.product_id)
        if not product:
            continue
        candidate_scores = []
        for candidate in stores:
            inv = inventory_map.get((candidate.id, product.id))
            dist = haversine_km(record.customer_lat, record.customer_lng, candidate.latitude, candidate.longitude)
            if dist < 18 and inv:
                available = max(0, inv.reported_quantity - inv.reserved_quantity)
                demand = 1.4 if product.category in ("Grocery", "Beverages", "Snacks", "Fruits", "Vegetables") else 0.8
                confidence = 100 * (0.72 * logistic((available - record.quantity - demand * 0.55) * 0.34) + 0.28 * inv.inventory_accuracy)
                adequacy = min(100, 100 * available / max(1, record.quantity + demand))
                distance_score = max(0, 100 * (1 - dist / 18))
                future_score = 100 * logistic((available - record.quantity - demand) * 0.34)
                delivery_score = max(20, 100 - dist * 5.5)
                score = sum((
                    weights["availability"] * confidence,
                    weights["inventory"] * adequacy,
                    weights["distance"] * distance_score,
                    weights["future_availability"] * future_score,
                    weights["delivery_sla"] * delivery_score,
                )) / 100
                candidate_scores.append((score, candidate.id, dist, available, inv.inventory_accuracy))
        chosen = max(candidate_scores, default=(0, nearest.id, 0, 0, 0), key=lambda row: row[0])
        chosen_id = chosen[1]
        # Recorded outcome is the observed positive label; for different stores we
        # estimate from their inventory snapshot and keep the metric definition explicit.
        baseline_inv = inventory_map.get((nearest.id, product.id))
        fiq_inv = inventory_map.get((chosen_id, product.id))
        baseline_success = bool(record.fulfilled) if nearest.id == record.store_id else bool(
            baseline_inv and baseline_inv.reported_quantity - baseline_inv.reserved_quantity >= record.quantity
            and baseline_inv.inventory_accuracy >= 0.8
        )
        fiq_success = bool(record.fulfilled) if chosen_id == record.store_id else bool(
            fiq_inv and fiq_inv.reported_quantity - fiq_inv.reserved_quantity >= record.quantity
            and fiq_inv.inventory_accuracy >= 0.8
        )
        baseline_ok += int(baseline_success)
        fiq_ok += int(fiq_success)
        baseline_dist.append(haversine_km(record.customer_lat, record.customer_lng, nearest.latitude, nearest.longitude))
        fiq_dist.append(chosen[2] if candidate_scores else haversine_km(record.customer_lat, record.customer_lng, nearest.latitude, nearest.longitude))
    n = max(1, len(records))
    return {
        "sample_size": len(records),
        "baseline": {"strategy": "Nearest store", "successful_fulfillment_rate": round(100 * baseline_ok / n, 1),
                     "average_distance_km": round(float(np.mean(baseline_dist)), 2), "stockout_rate": round(100 * (1 - baseline_ok / n), 1)},
        "fulfilliq": {"strategy": "FulfillIQ score", "successful_fulfillment_rate": round(100 * fiq_ok / n, 1),
                      "average_distance_km": round(float(np.mean(fiq_dist)), 2), "stockout_rate": round(100 * (1 - fiq_ok / n), 1)},
        "note": "Computed on a 250-order generated-data slice. For candidates other than the recorded store, outcomes use the current inventory snapshot; this is a prototype simulation, not a production experiment.",
    }


@app.get("/recommendations")
async def global_recommendations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    stmt = select(Recommendation).options(selectinload(Recommendation.store), selectinload(Recommendation.product)).order_by(Recommendation.created_at.desc())
    if user.role == RoleEnum.STORE_MANAGER:
        stmt = stmt.where(Recommendation.store_id == user.store_id)
    elif user.role == RoleEnum.CUSTOMER:
        raise HTTPException(status_code=403, detail="Recommendations are for store teams and platform admins.")
    recommendations = (await db.scalars(stmt.limit(200))).all()
    return [recommendation_payload(r) for r in recommendations]


@app.get("/admin/transfers")
async def list_transfers(user: User = Depends(require_roles(RoleEnum.PLATFORM_ADMIN)), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(StoreTransfer).order_by(StoreTransfer.created_at.desc()).limit(100))).all()
    return [{"id": r.id, "from_store_id": r.from_store_id, "to_store_id": r.to_store_id, "product_id": r.product_id,
             "quantity": r.quantity, "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]


# In the Render image, the Vite build is copied beside the backend. Keep API
# routes first, then serve assets and let React Router handle browser routes.
static_dir = Path(__file__).resolve().parents[1] / "static"
if static_dir.is_dir():
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{requested_path:path}", include_in_schema=False)
    async def frontend_fallback(requested_path: str):
        candidate = (static_dir / requested_path).resolve()
        try:
            candidate.relative_to(static_dir.resolve())
        except ValueError:
            candidate = static_dir / "index.html"
        if not candidate.is_file():
            candidate = static_dir / "index.html"
        return FileResponse(candidate)
