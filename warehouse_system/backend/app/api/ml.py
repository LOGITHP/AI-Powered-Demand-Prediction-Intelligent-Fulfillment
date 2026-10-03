from fastapi import APIRouter, Depends
from app.schemas import MLPredictionRequest
from app.ml.services import (
    predict_labour_requirement,
    predict_processing_time,
    predict_delay_probability,
    predict_congestion_probability
)
from app.api.auth import get_current_user

router = APIRouter()

@router.post("/labour/predict")
def predict_labour(request: MLPredictionRequest, current_user = Depends(get_current_user)):
    prediction = predict_labour_requirement(request)
    return {"prediction": prediction, "model": "labour_requirement", "warehouse_id": request.warehouse_id, "process_type": request.process_type}

@router.post("/processing/predict")
def predict_processing(request: MLPredictionRequest, current_user = Depends(get_current_user)):
    prediction = predict_processing_time(request)
    return {"prediction": prediction, "model": "processing_time", "warehouse_id": request.warehouse_id, "process_type": request.process_type}

@router.post("/delay/predict")
def predict_delay(request: MLPredictionRequest, current_user = Depends(get_current_user)):
    status, prob = predict_delay_probability(request)
    return {"probability": prob, "status": "HIGH_RISK" if status == 1 else "LOW_RISK", "model": "delay_risk"}

@router.post("/congestion/predict")
def predict_congestion(request: MLPredictionRequest, current_user = Depends(get_current_user)):
    status, prob = predict_congestion_probability(request)
    return {"probability": prob, "status": "CONGESTED" if status == 1 else "NORMAL", "model": "congestion"}
