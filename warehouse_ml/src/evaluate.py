import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import datetime

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def evaluate_regression(y_true, y_pred, model_name, target):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    print(f"--- {model_name} on {target} ---")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R2:   {r2:.4f}")
    
    return {'MAE': mae, 'RMSE': rmse, 'R2': r2}

def evaluate_classification(y_true, y_pred, y_prob, model_name, target):
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    roc_auc = roc_auc_score(y_true, y_prob) if y_prob is not None else None
    pr_auc = average_precision_score(y_true, y_prob) if y_prob is not None else None
    
    print(f"--- {model_name} on {target} ---")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")
    if roc_auc: print(f"ROC-AUC:   {roc_auc:.4f}")
    if pr_auc: print(f"PR-AUC:    {pr_auc:.4f}")
    
    metrics = {'precision': precision, 'recall': recall, 'F1': f1, 'ROC_AUC': roc_auc, 'PR_AUC': pr_auc}
    return metrics

def save_model_metadata(model_name, target, algorithm, metrics, features, is_regression=True):
    csv_path = os.path.join(MODELS_DIR, 'model_comparison.csv')
    
    # Save to CSV
    record = {
        'model_name': model_name,
        'target': target,
        'algorithm': algorithm,
        'MAE': metrics.get('MAE', ''),
        'RMSE': metrics.get('RMSE', ''),
        'R2': metrics.get('R2', ''),
        'precision': metrics.get('precision', ''),
        'recall': metrics.get('recall', ''),
        'F1': metrics.get('F1', ''),
        'ROC_AUC': metrics.get('ROC_AUC', ''),
        'PR_AUC': metrics.get('PR_AUC', '')
    }
    
    df = pd.DataFrame([record])
    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode='a', header=False, index=False)
    else:
        df.to_csv(csv_path, index=False)
        
    # Save to JSON
    json_path = os.path.join(MODELS_DIR, 'model_metadata.json')
    meta = []
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            try:
                meta = json.load(f)
            except:
                meta = []
                
    meta.append({
        'model_name': model_name,
        'target': target,
        'algorithm': algorithm,
        'features_used': features,
        'training_date': datetime.datetime.now().isoformat(),
        'dataset_version': '1.0',
        'evaluation_metrics': metrics,
        'random_seed': 42
    })
    
    with open(json_path, 'w') as f:
        json.dump(meta, f, indent=4)

def plot_feature_importance(model, preprocessor, num_features, cat_features, title, save_name):
    try:
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            
            # Get feature names after preprocessing
            # Numeric features remain the same
            cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
            cat_encoded_features = list(cat_encoder.get_feature_names_out(cat_features))
            all_features = num_features + cat_encoded_features
            
            if len(importances) == len(all_features):
                df_imp = pd.DataFrame({'Feature': all_features, 'Importance': importances})
                df_imp = df_imp.sort_values(by='Importance', ascending=False).head(15)
                
                plt.figure(figsize=(10, 6))
                sns.barplot(x='Importance', y='Feature', data=df_imp)
                plt.title(f'Feature Importance - {title}')
                plt.tight_layout()
                plt.savefig(os.path.join(REPORTS_DIR, save_name))
                plt.close()
    except Exception as e:
        print(f"Could not plot feature importance: {e}")

def plot_confusion_matrix(y_true, y_pred, title, save_name):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'Confusion Matrix - {title}')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, save_name))
    plt.close()
