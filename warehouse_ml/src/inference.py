import pandas as pd
import joblib
import os
from preprocess import feature_engineering

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')

def load_pipeline(model_filename):
    model_path = os.path.join(MODELS_DIR, model_filename)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file {model_path} not found. Please train it first.")
    return joblib.load(model_path)

def prepare_input(input_data, pipeline):
    df = pd.DataFrame([input_data])
    df_engineered = feature_engineering(df)
    
    # Ensure categorical features match types (e.g., string vs int)
    if 'shift' in df_engineered.columns:
        df_engineered['shift'] = df_engineered['shift'].astype(int)
        
    num_features = pipeline['num_features']
    cat_features = pipeline['cat_features']
    
    X = df_engineered[num_features + cat_features]
    X_processed = pipeline['preprocessor'].transform(X)
    return X_processed

def predict_required_workers(input_data):
    pipeline = load_pipeline('labour_requirement_model.pkl')
    X_processed = prepare_input(input_data, pipeline)
    prediction = pipeline['model'].predict(X_processed)[0]
    return int(round(prediction))

def predict_processing_time(input_data):
    pipeline = load_pipeline('processing_time_model.pkl')
    X_processed = prepare_input(input_data, pipeline)
    prediction = pipeline['model'].predict(X_processed)[0]
    return float(prediction)

def predict_delay_probability(input_data):
    pipeline = load_pipeline('delay_risk_model.pkl')
    X_processed = prepare_input(input_data, pipeline)
    
    model = pipeline['model']
    prediction = model.predict(X_processed)[0]
    
    prob = None
    if hasattr(model, 'predict_proba'):
        prob = model.predict_proba(X_processed)[0][1]
        
    return int(prediction), float(prob) if prob is not None else None

def predict_congestion_probability(input_data):
    pipeline = load_pipeline('congestion_model.pkl')
    X_processed = prepare_input(input_data, pipeline)
    
    model = pipeline['model']
    prediction = model.predict(X_processed)[0]
    
    prob = None
    if hasattr(model, 'predict_proba'):
        prob = model.predict_proba(X_processed)[0][1]
        
    return int(prediction), float(prob) if prob is not None else None

if __name__ == '__main__':
    # Example usage
    sample_input = {
        'date': '2023-07-01',
        'warehouse_id': 'WH01',
        'shift': 1,
        'process_type': 'PICKING',
        'workload_quantity': 8000,
        'number_of_orders': 1600,
        'number_of_items': 8000,
        'number_of_skus': 800,
        'scheduled_workers': 15,
        'available_workers': 15,
        'average_worker_experience': 3.5,
        'average_worker_skill': 1.1,
        'equipment_available': 0.9,
        'current_queue': 1200,
        'warehouse_utilization': 0.85,
        'historical_productivity': 400.0,
        'distance_factor': 1.0,
        'task_complexity': 1.0
    }
    
    print("Example Prediction:")
    print("Input:", sample_input)
    print("\nOutputs:")
    
    try:
        req_workers = predict_required_workers(sample_input)
        print(f"required_workers = {req_workers}")
        
        proc_time = predict_processing_time(sample_input)
        print(f"processing_time = {proc_time:.2f} minutes")
        
        delay_pred, delay_prob = predict_delay_probability(sample_input)
        print(f"delay_probability = {delay_prob:.4f} (Status: {delay_pred})")
        
        cong_pred, cong_prob = predict_congestion_probability(sample_input)
        print(f"congestion_probability = {cong_prob:.4f} (Status: {cong_pred})")
    except Exception as e:
        print("Error running predictions. Ensure models are trained first.", e)
