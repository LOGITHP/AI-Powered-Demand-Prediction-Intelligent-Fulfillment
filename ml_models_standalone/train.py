import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, f1_score, roc_auc_score

def train_models():
    print("Loading dataset...")
    try:
        df = pd.read_csv("historical_orders.csv")
    except FileNotFoundError:
        print("Error: historical_orders.csv not found. Run generate_dataset.py first.")
        return
        
    print(f"Loaded {len(df)} rows.")

    # ---------------------------------------------------------
    # 1. Demand Prediction Model (Regression)
    # Predicts the `quantity_demanded`
    # ---------------------------------------------------------
    print("\n--- Training Demand Prediction Model ---")
    demand_features = ["product_id", "store_id", "hour", "day_of_week", "month", "is_weekend", "promotion_flag", "inventory_before_order"]
    X_demand = df[demand_features].values
    y_demand = df["quantity_demanded"].values

    X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(X_demand, y_demand, test_size=0.2, random_state=42)

    demand_model = RandomForestRegressor(n_estimators=70, max_depth=15, min_samples_leaf=3, random_state=42, n_jobs=-1)
    demand_model.fit(X_train_d, y_train_d)
    
    d_preds = demand_model.predict(X_test_d)
    print(f"Demand Model MAE: {mean_absolute_error(y_test_d, d_preds):.3f}")
    print(f"Demand Model R2 Score: {r2_score(y_test_d, d_preds):.3f}")
    
    joblib.dump(demand_model, "demand_model.joblib")
    print("Saved demand model to demand_model.joblib")

    # ---------------------------------------------------------
    # 2. Availability Prediction Model (Classification)
    # Predicts whether an order will be `fulfilled` (1 or 0)
    # ---------------------------------------------------------
    print("\n--- Training Availability Classification Model ---")
    avail_features = ["inventory_before_order", "quantity_demanded", "inventory_accuracy", "inventory_age_hours", "sales_velocity", "hour", "day_of_week", "store_id", "product_id"]
    X_avail = df[avail_features].values
    y_avail = df["fulfilled"].values

    X_train_a, X_test_a, y_train_a, y_test_a = train_test_split(X_avail, y_avail, test_size=0.2, random_state=42, stratify=y_avail)

    avail_model = RandomForestClassifier(n_estimators=70, max_depth=15, min_samples_leaf=3, class_weight="balanced", random_state=42, n_jobs=-1)
    avail_model.fit(X_train_a, y_train_a)

    a_preds = avail_model.predict(X_test_a)
    a_proba = avail_model.predict_proba(X_test_a)[:, 1]
    
    print(f"Availability Accuracy: {accuracy_score(y_test_a, a_preds):.3f}")
    print(f"Availability F1 Score: {f1_score(y_test_a, a_preds):.3f}")
    print(f"Availability ROC AUC: {roc_auc_score(y_test_a, a_proba):.3f}")

    joblib.dump(avail_model, "availability_model.joblib")
    print("Saved availability model to availability_model.joblib")
    print("\nAll models trained and exported successfully!")

if __name__ == "__main__":
    train_models()
