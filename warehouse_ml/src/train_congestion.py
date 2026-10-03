import pandas as pd
import numpy as np
import os
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from preprocess import get_features_and_target, get_preprocessor
from evaluate import evaluate_classification, save_model_metadata, plot_feature_importance, plot_confusion_matrix

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')

def main():
    print("--- Training Congestion Prediction Model ---")
    train_df = pd.read_csv(os.path.join(DATA_DIR, 'train.csv'))
    val_df = pd.read_csv(os.path.join(DATA_DIR, 'validation.csv'))
    test_df = pd.read_csv(os.path.join(DATA_DIR, 'test.csv'))
    
    target_col = 'congestion_status'
    
    X_train, y_train, num_features, cat_features = get_features_and_target(train_df, target_col, 'congestion')
    X_val, y_val, _, _ = get_features_and_target(val_df, target_col, 'congestion')
    X_test, y_test, _, _ = get_features_and_target(test_df, target_col, 'congestion')
    
    preprocessor = get_preprocessor(num_features, cat_features)
    X_train_processed = preprocessor.fit_transform(X_train)
    X_val_processed = preprocessor.transform(X_val)
    X_test_processed = preprocessor.transform(X_test)
    
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000),
        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
        'XGBoost': XGBClassifier(n_estimators=100, random_state=42, use_label_encoder=False, eval_metric='logloss')
    }
    
    best_model = None
    best_f1 = -1
    best_model_name = ""
    
    for name, model in models.items():
        model.fit(X_train_processed, y_train)
        y_val_pred = model.predict(X_val_processed)
        y_val_prob = model.predict_proba(X_val_processed)[:, 1] if hasattr(model, "predict_proba") else None
        
        metrics = evaluate_classification(y_val, y_val_pred, y_val_prob, name, target_col)
        
        if metrics['F1'] > best_f1:
            best_f1 = metrics['F1']
            best_model = model
            best_model_name = name

    print(f"Best model based on Validation F1: {best_model_name}")
    
    y_test_pred = best_model.predict(X_test_processed)
    y_test_prob = best_model.predict_proba(X_test_processed)[:, 1] if hasattr(best_model, "predict_proba") else None
    test_metrics = evaluate_classification(y_test, y_test_pred, y_test_prob, f"TEST - {best_model_name}", target_col)
    
    full_pipeline = {
        'preprocessor': preprocessor,
        'model': best_model,
        'num_features': num_features,
        'cat_features': cat_features
    }
    
    model_path = os.path.join(MODELS_DIR, 'congestion_model.pkl')
    joblib.dump(full_pipeline, model_path)
    print(f"Model saved to {model_path}")
    
    save_model_metadata('congestion_model', target_col, best_model_name, test_metrics, num_features + cat_features, is_regression=False)
    plot_feature_importance(best_model, preprocessor, num_features, cat_features, 'Congestion Prediction', 'feature_imp_congestion.png')
    plot_confusion_matrix(y_test, y_test_pred, 'Congestion Prediction', 'confusion_matrix_congestion.png')

if __name__ == '__main__':
    main()
