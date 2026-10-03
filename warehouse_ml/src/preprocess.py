import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

def feature_engineering(df):
    """Create meaningful derived features."""
    df = df.copy()
    
    # Ensure no zero division
    avail_workers = df['available_workers'].replace(0, 1)
    
    # Derived features
    if 'required_workers' in df.columns:
        df['worker_shortage'] = df['required_workers'] - df['available_workers'] 
    # WAIT! required_workers is Label 1. Using it in feature_engineering causes leakage for other models if we are not careful.
    # Actually, worker_shortage as defined in the prompt uses `required_workers`. If a model uses worker_shortage to predict Delay, it's theoretically leakage if `required_workers` is not known at prediction time. But the prompt explicitly asks for:
    # worker_shortage = required_workers - available_workers
    # So we'll calculate it, but the models must carefully select which features to use!
    
    df['workload_per_worker'] = df['workload_quantity'] / avail_workers
    df['queue_per_worker'] = df['current_queue'] / avail_workers
    
    # Estimated processing capacity (historical * available workers)
    est_capacity = df['historical_productivity'] * avail_workers * 7.5 # 7.5 hrs per shift
    df['capacity_ratio'] = df['workload_quantity'] / est_capacity.replace(0, 1)
    
    # worker_utilization based on capacity
    df['worker_utilization'] = df['workload_quantity'] / est_capacity.replace(0, 1)
    
    # Extract temporal features from date
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    
    return df

def get_preprocessor(numeric_features, categorical_features):
    """Create a standard scikit-learn preprocessing pipeline."""
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    
    return preprocessor

def get_features_and_target(df, target_col, task_type='labour'):
    """
    Returns X and y. Selects features based on the task to prevent data leakage.
    """
    df_engineered = feature_engineering(df)
    
    # Universal Input Features (known before shift starts)
    base_num_features = [
        'workload_quantity', 'number_of_orders', 'number_of_items', 'number_of_skus',
        'scheduled_workers', 'available_workers', 'average_worker_experience',
        'average_worker_skill', 'equipment_available', 'current_queue', 
        'warehouse_utilization', 'historical_productivity', 'distance_factor', 
        'task_complexity', 'workload_per_worker', 'queue_per_worker',
        'capacity_ratio', 'worker_utilization', 'day_of_week', 'is_weekend'
    ]
    
    base_cat_features = ['warehouse_id', 'shift', 'process_type']
    
    # Task specific adjustments to prevent leakage
    num_features = base_num_features.copy()
    cat_features = base_cat_features.copy()
    
    # We DO NOT include labels in features: 
    # 'required_workers', 'processing_time_minutes', 'delay_status', 'congestion_status', 'worker_productivity'
    # Also, we should only include 'worker_shortage' if we are predicting something where 'required_workers' is ALREADY predicted or given. 
    # For safety against leakage, let's omit 'worker_shortage' unless explicitly safe.
    
    if task_type == 'labour':
        # Target: required_workers
        pass 
    elif task_type == 'processing_time':
        # Target: processing_time_minutes
        pass
    elif task_type == 'delay':
        # Target: delay_status
        pass
    elif task_type == 'congestion':
        # Target: congestion_status
        pass

    # Ensure no targets are in features
    targets = ['required_workers', 'processing_time_minutes', 'delay_status', 'congestion_status', 'worker_productivity']
    num_features = [f for f in num_features if f not in targets]
    
    X = df_engineered[num_features + cat_features]
    y = df_engineered[target_col]
    
    return X, y, num_features, cat_features
