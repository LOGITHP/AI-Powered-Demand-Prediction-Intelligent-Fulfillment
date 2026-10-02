from fastapi import APIRouter
from app.api import auth, products, stores, recommend, ml

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(stores.router, prefix="/stores", tags=["stores"])
api_router.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
api_router.include_router(ml.router, prefix="/admin/models", tags=["ml"])
