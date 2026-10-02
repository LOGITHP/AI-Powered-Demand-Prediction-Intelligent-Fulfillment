# Machine learning

The integrated trainers are part of the backend application so training, evaluation, version metadata and activation share one API and database.

- Demand: RandomForestRegressor over generated product, store, time and inventory features; evaluated with MAE, RMSE and R².
- Availability: RandomForestClassifier over stock, requested quantity, inventory reliability/freshness, recent sales velocity, store and product; evaluated with accuracy, precision, recall, F1 and ROC-AUC.

Models are saved as Joblib files under MODEL_STORAGE_PATH. An active model is distinct from a saved model. Until activation, predictions use labeled baseline calculations. All metrics are generated-data metrics, not real-world claims.
