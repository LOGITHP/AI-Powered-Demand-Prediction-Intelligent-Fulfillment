import pandas as pd
import numpy as np
import os
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from preprocess import get_features_and_target, get_preprocessor
from evaluate import evaluate_regression, save_model_metadata, plot_feature_importance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')

def main():
    print("--- Training Labour Requirement Model ---")
    train_df = pd.read_csv(os.path.join(DATA_DIR, 'train.csv'))
    val_df = pd.read_csv(os.path.join(DATA_DIR, 'validation.csv'))
    test_df = pd.read_csv(os.path.join(DATA_DIR, 'test.csv'))
    
    target_col = 'required_workers'
    
    X_train, y_train, num_features, cat_features = get_features_and_target(train_df, target_col, 'labour')
    X_val, y_val, _, _ = get_features_and_target(val_df, target_col, 'labour')
    X_test, y_test, _, _ = get_features_and_target(test_df, target_col, 'labour')
    
    preprocessor = get_preprocessor(num_features, cat_features)
    X_train_processed = preprocessor.fit_transform(X_train)
    X_val_processed = preprocessor.transform(X_val)
    X_test_processed = preprocessor.transform(X_test)
    
    # Train models
    models = {
        'LinearRegression': LinearRegression(),
        'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
        'XGBoost': XGBRegressor(n_estimators=100, random_state=42)
    }
    
    best_model = None
    best_rmse = float('inf')
    best_model_name = ""
    
    for name, model in models.items():
        model.fit(X_train_processed, y_train)
        y_val_pred = model.predict(X_val_processed)
        metrics = evaluate_regression(y_val, y_val_pred, name, target_col)
        
        if metrics['RMSE'] < best_rmse:
            best_rmse = metrics['RMSE']
            best_model = model
            best_model_name = name

    print(f"Best model based on Validation RMSE: {best_model_name}")
    
    # Evaluate best model on test set
    y_test_pred = best_model.predict(X_test_processed)
    test_metrics = evaluate_regression(y_test, y_test_pred, f"TEST - {best_model_name}", target_col)
    
    # Save best model and metadata
    full_pipeline = {
        'preprocessor': preprocessor,
        'model': best_model,
        'num_features': num_features,
        'cat_features': cat_features
    }
    
    model_path = os.path.join(MODELS_DIR, 'labour_requirement_model.pkl')
    joblib.dump(full_pipeline, model_path)
    print(f"Model saved to {model_path}")
    
    save_model_metadata('labour_requirement_model', target_col, best_model_name, test_metrics, num_features + cat_features, is_regression=True)
    
    plot_feature_importance(best_model, preprocessor, num_features, cat_features, 'Labour Requirement Prediction', 'feature_imp_labour.png')

if __name__ == '__main__':
    main()
