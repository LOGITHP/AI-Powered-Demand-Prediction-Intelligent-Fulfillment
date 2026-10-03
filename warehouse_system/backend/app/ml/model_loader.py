import os
import joblib
import pandas as pd
from app.core.config import settings

class ModelLoader:
    _instances = {}

    @classmethod
    def get_pipeline(cls, model_name: str):
        if model_name not in cls._instances:
            path = os.path.join(settings.ML_MODELS_PATH, f"{model_name}.pkl")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Model {path} not found")
            cls._instances[model_name] = joblib.load(path)
        return cls._instances[model_name]

def feature_engineering(df):
    """Must strictly match the one used during training."""
    df = df.copy()
    avail_workers = df['available_workers'].replace(0, 1)
    
    if 'required_workers' in df.columns:
        df['worker_shortage'] = df['required_workers'] - df['available_workers'] 
    
    df['workload_per_worker'] = df['workload_quantity'] / avail_workers
    df['queue_per_worker'] = df['current_queue'] / avail_workers
    
    est_capacity = df['historical_productivity'] * avail_workers * 7.5
    df['capacity_ratio'] = df['workload_quantity'] / est_capacity.replace(0, 1)
    df['worker_utilization'] = df['workload_quantity'] / est_capacity.replace(0, 1)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    else:
        # Defaults if date is missing
        df['day_of_week'] = 0
        df['is_weekend'] = 0
        
    return df

def prepare_input(input_data: dict, pipeline):
    df = pd.DataFrame([input_data])
    df_engineered = feature_engineering(df)
    
    if 'shift' in df_engineered.columns:
        df_engineered['shift'] = df_engineered['shift'].astype(int)
        
    num_features = pipeline['num_features']
    cat_features = pipeline['cat_features']
    
    # Fill missing features with 0 to avoid KeyError if the payload doesn't provide them
    for col in num_features + cat_features:
        if col not in df_engineered.columns:
            df_engineered[col] = 0
            
    X = df_engineered[num_features + cat_features]
    X_processed = pipeline['preprocessor'].transform(X)
    return X_processed
