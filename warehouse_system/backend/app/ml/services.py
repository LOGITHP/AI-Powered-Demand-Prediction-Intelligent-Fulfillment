from app.ml.model_loader import ModelLoader, prepare_input
from app.schemas import MLPredictionRequest

def predict_labour_requirement(request: MLPredictionRequest) -> int:
    pipeline = ModelLoader.get_pipeline('labour_requirement_model')
    X_processed = prepare_input(request.dict(), pipeline)
    prediction = pipeline['model'].predict(X_processed)[0]
    return max(1, int(round(prediction)))

def predict_processing_time(request: MLPredictionRequest) -> float:
    pipeline = ModelLoader.get_pipeline('processing_time_model')
    X_processed = prepare_input(request.dict(), pipeline)
    prediction = pipeline['model'].predict(X_processed)[0]
    return float(prediction)

def predict_delay_probability(request: MLPredictionRequest):
    pipeline = ModelLoader.get_pipeline('delay_risk_model')
    X_processed = prepare_input(request.dict(), pipeline)
    model = pipeline['model']
    prediction = model.predict(X_processed)[0]
    prob = model.predict_proba(X_processed)[0][1] if hasattr(model, 'predict_proba') else None
    return int(prediction), float(prob) if prob is not None else None

def predict_congestion_probability(request: MLPredictionRequest):
    pipeline = ModelLoader.get_pipeline('congestion_model')
    X_processed = prepare_input(request.dict(), pipeline)
    model = pipeline['model']
    prediction = model.predict(X_processed)[0]
    prob = model.predict_proba(X_processed)[0][1] if hasattr(model, 'predict_proba') else None
    return int(prediction), float(prob) if prob is not None else None
