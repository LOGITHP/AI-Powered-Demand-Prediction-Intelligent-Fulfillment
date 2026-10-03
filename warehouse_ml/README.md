# AI-Assisted Warehouse Management System - ML Pipeline

This project contains a complete synthetic data generation and machine learning training pipeline for an AI-assisted Warehouse Management System.

## Project Structure
```
warehouse_ml/
│
├── data/                       # Generated synthetic datasets (train/val/test)
├── models/                     # Saved ML models, metadata, and comparisons
├── notebooks/                  # (Optional) Jupyter notebooks for EDA
├── reports/                    # Generated charts, confusion matrices, and feature importance plots
├── src/                        # Python source code
│   ├── generate_data.py        # Simulates warehouse operations and creates dataset
│   ├── preprocess.py           # Feature engineering and scaling/encoding pipeline
│   ├── train_labour.py         # Trains model to predict required workers
│   ├── train_processing.py     # Trains model to predict processing time
│   ├── train_delay.py          # Trains model to predict delay risk
│   ├── train_congestion.py     # Trains model to predict congestion risk
│   ├── evaluate.py             # Evaluation metrics and plotting functions
│   └── inference.py            # Functions for real-time predictions
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

## Setup and Execution

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the full pipeline:**
   Execute the scripts in the following order:
   ```bash
   # 1. Generate the synthetic data (creates CSVs in data/)
   python src/generate_data.py
   
   # 2. Train and evaluate the models
   python src/train_labour.py
   python src/train_processing.py
   python src/train_delay.py
   python src/train_congestion.py
   
   # 3. Test Inference
   python src/inference.py
   ```

## Report

### 1. How the synthetic warehouse was simulated
The simulation creates 5 unique warehouses with varying characteristics (capacity, efficiency, congestion sensitivity). It simulates 500 workers with different skill levels (Beginner, Intermediate, Expert) and attendance probabilities. Over a 180-day period across 3 shifts per day, workload variations are generated incorporating day-of-week trends and occasional volume spikes. The processes (Receiving, Inspection, Putaway, Picking, Packing, Loading) operate on varying baseline productivities modified by worker skills, available equipment, and warehouse congestion.

### 2. How each label was generated
* **`required_workers`**: Calculated logically from `workload_quantity / (effective_productivity_per_worker * productive_shift_hours)`. The effective productivity incorporates worker skill, equipment, and congestion penalties. It represents the *true* number of workers needed to clear the volume in one shift.
* **`processing_time_minutes`**: Calculated from `workload_quantity / total_effective_capacity_per_hour` for the *actual available workers* + time to clear the existing queue.
* **`delay_status`**: Set to `1` if the calculated `processing_time_minutes` exceeds the standard shift service time (480 minutes), otherwise `0`.
* **`congestion_status`**: Set to `1` if the warehouse utilization exceeds 90% or the queue length exceeds 50% of the shift's processing capacity.

### 3. Features used by each model
The models use a common set of features available *before* a shift begins, strictly avoiding data leakage from target variables.
* **Core features**: `workload_quantity`, `number_of_orders`, `number_of_items`, `number_of_skus`, `scheduled_workers`, `available_workers`, `average_worker_experience`, `average_worker_skill`, `equipment_available`, `current_queue`, `warehouse_utilization`, `historical_productivity`, `distance_factor`, `task_complexity`.
* **Derived features**: `workload_per_worker`, `queue_per_worker`, `capacity_ratio`, `worker_utilization`, `day_of_week`, `is_weekend`.
* **Categorical features**: `warehouse_id`, `shift`, `process_type`.

### 4. Why each algorithm was selected
For each task, we compared a simple baseline against tree-based ensembles (Random Forest and XGBoost). 
* **Linear/Logistic Regression** serve as interpretable baselines to check for simple linear correlations.
* **Random Forest** captures non-linear relationships and interactions between features without needing extensive tuning, highly robust to outliers.
* **XGBoost** typically provides the best predictive performance for tabular data by sequentially minimizing errors, successfully modeling the complex logical relationships in the synthetic simulation. 
The *best* model is selected dynamically based on Validation Set performance (RMSE for regression, F1-Score for classification) to be saved and used for inference.

### 5. Evaluation Results
Evaluation results (MAE, RMSE, R2, Precision, Recall, F1, AUC) are printed during the training scripts execution. 
They are also persistently logged in `models/model_comparison.csv` and `models/model_metadata.json`. Feature importance charts and confusion matrices are saved as PNGs in the `reports/` folder.

### 6. Potential Data Leakage
Great care was taken to avoid data leakage. The `required_workers`, `processing_time_minutes`, `delay_status`, `congestion_status`, and `worker_productivity` columns are exclusively targets. They are dynamically stripped from the feature set via `preprocess.get_features_and_target`. We explicitly avoided using `required_workers` to generate an input feature `worker_shortage` (despite it being defined theoretically), because knowing `required_workers` perfectly implies the label.

### 7. Model Limitations
* The dataset is entirely synthetic, built on mathematical assumptions and normal distributions. Real warehouses contain noisy, unstructured disruptions (e.g., system outages, sudden weather events, accidents).
* Skill and Experience are currently averaged per shift, which aggregates away individual high-performer vs low-performer dynamics that might specifically bottleneck a single task.

### 8. Connection to a Warehouse Agent
These ML models are designed to act as the "brain" of a predictive Warehouse Agent. 
* At the beginning of a shift, the agent ingests ERP data (expected inbound/outbound volume) and HR data (rostered workers).
* It passes this payload to `predict_required_workers` to identify if the scheduled roster is sufficient.
* If a shortage is detected, it queries `predict_delay_probability` and `predict_congestion_probability`. If these probabilities are high, the agent can autonomously trigger alerts, request casual labor, or reroute inbound trucks to different warehouse zones.
* The functions exposed in `inference.py` are stateless and can easily be wrapped in a REST API (e.g., FastAPI) for seamless integration into the Agent's decision loop.
