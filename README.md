# FulfillIQ

FulfillIQ is a runnable prototype for retail availability and fulfillment decisions. It estimates whether a requested quantity is likely to be on hand, forecasts demand, scores nearby simulated locations and recommends a store. All stores, products, customers, inventory and orders are fictional.

## Quick start with Docker

Requirements: Docker Desktop with Compose.

1. From this directory, copy .env.example to .env. Change JWT_SECRET before sharing the environment.
2. Start the services:

        docker compose up --build

3. Open:
   - Customer and operations UI: http://localhost:5173
   - FastAPI Swagger: http://localhost:8000/docs
   - Health: http://localhost:8000/health

On first startup the API creates its schema and seeds 508 products, 50 simulated Coimbatore locations, inventory, inventory events, 30,000 historical order examples and demo accounts. The initial seed can take a minute. PostgreSQL data is retained in the postgres_data volume. Stop with Ctrl+C; use docker compose down to stop containers.

## Deploy to Render

The repository-root `render.yaml` defines one web service plus a managed PostgreSQL database. The web service builds the React app into the FastAPI image, so the UI and API share one public URL and do not need a separately configured CORS origin.

1. Push this repository to a Git provider connected to Render.
2. In the Render Dashboard, create a new Blueprint and select this repository. Render reads `render.yaml` from the repository root.
3. Review the `fulfilliq` web service and `fulfilliq-db` database, then apply the Blueprint. Render generates `JWT_SECRET` and supplies the database connection string.
4. When the deploy is healthy, open the web service's `onrender.com` URL. The API health endpoint is `/health` and Swagger is `/docs`.

The Blueprint selects Render's free plans for a prototype. The web service sleeps after 15 minutes without traffic, and the free Postgres database expires 30 days after creation. Trained model files use the container's temporary filesystem and can be lost on restart or redeploy; the Postgres database stores the app's operational data. Upgrade the database before the 30-day expiry if you need to retain it, and use paid compute plus persistent storage for production-style uptime or durable model artifacts.

The login screen includes shared demo credentials, including a platform-admin account. The seeded data is fictional; anyone with those credentials can change the demo records. Change the demo credentials or restrict access before sharing the URL broadly.

## Run locally without Docker

Python 3.11+ and Node.js 20+ are recommended. PostgreSQL is optional for local development; SQLite is the default.

PowerShell:

    Copy-Item .env.example backend/.env
    py -3.11 -m venv backend/venv
    .\backend\venv\Scripts\Activate.ps1
    pip install -r backend/requirements.txt
    Set-Location backend
    alembic upgrade head
    uvicorn app.main:app --reload

In a second terminal:

    Set-Location frontend
    npm install
    npm run dev

The API creates any missing tables and seeds the demo dataset on first startup. backend/scripts/generate_data.py safely initializes an empty database and does not delete existing records. If you copied .env.example to backend/.env, its SQLite URL will create backend/fulfilliq.db.

## Demo accounts

These development-only accounts are seeded automatically.

| Role | Email | Access |
| --- | --- | --- |
| Platform admin | admin@fulfilliq.local | FulfillIQ-demo-2026! |
| Store manager | manager01@fulfilliq.local | FulfillIQ-demo-2026! |
| Customer | customer@fulfilliq.local | FulfillIQ-demo-2026! |

Public registration creates customer accounts only. Admin and store-manager permissions cannot be chosen at registration.

## Demo flow

1. Sign in as the customer or browse without signing in.
2. Search Wireless Mouse. Choose a nearby recommendation to see availability confidence, estimated distance, a transparent fulfillment score, and alternative stores.
3. Add the item to the bag and sign in as the customer to place a demo order. No real payment is collected; on-hand inventory is reduced and a sale event is recorded.
4. Sign in as the platform admin to view the network map, predictions, order queue, analytics and simulation tools.
5. Sign in as the store manager to review store-specific stock, forecasts, recommendations and incoming orders.

The customer location starts at central Coimbatore (11.0168, 76.9558) and can be changed from the shop screen. Map distances use the Haversine straight-line estimate, not driving distance.

## Model training and evaluation

The model-training screen is available only to PLATFORM_ADMIN. Demand and availability use scikit-learn Random Forest baselines. Training stores versioned Joblib files and model metadata under MODEL_STORAGE_PATH; holdout MAE/RMSE/R² or accuracy/precision/recall/F1/ROC-AUC are computed from generated order records. Train and activate are separate actions. Until a trained model is activated, the API uses a transparent seasonal demand baseline and an inventory reliability availability baseline.

These results describe simulated data and are not production performance claims. Demand examples represent generated order records rather than a real point-of-sale feed. Business strategy comparison is a prototype simulation; the API response includes its sample size and methodology note.

The simulation screen can advance one simulated hour, add examples until the dataset reaches 100,000 records, or complete a store transfer. The initial reproducible seed is 42. Increasing generated data can take time.

## Environment variables

See .env.example.

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | Async SQLAlchemy URL; SQLite locally or PostgreSQL in Compose |
| JWT_SECRET | Signing secret for bearer tokens |
| CORS_ORIGINS | Comma-separated allowed browser origins |
| MODEL_STORAGE_PATH | Directory for saved Joblib model versions |
| SEED | Reproducible seed-data and simulation seed |
| HISTORICAL_ORDER_COUNT | First-start generated history count (prototype default: 30,000) |
| POSTGRES_PASSWORD | Local Compose-only PostgreSQL password |

The included .env.example values are for local demonstration. Use a private secret and database credentials for any shared deployment; never commit a real .env.

## Migrations and project map

Run migrations from backend/ after activating the environment:

    alembic upgrade head

The migration is also safe against a fresh database because schema creation is idempotent. FastAPI creates missing tables on startup as a local-development convenience.

    fulfilliq/
    ├── backend/app/        FastAPI, SQLAlchemy models, services, seed and Alembic migration
    ├── backend/scripts/    Safe seed-data initialization command
    ├── frontend/src/       React, TypeScript, customer/store/admin UI
    ├── database/           Database notes
    ├── docs/                Architecture overview
    ├── ml/                  Training notes; integrated trainers use backend/app
    ├── docker-compose.yml
    └── .env.example

The Render Blueprint is at the repository root, alongside the `fulfilliq/` directory.

## Notes

- Store names and locations are fictional examples distributed around Coimbatore, Tamil Nadu.
- Placeholder product art is not a product photograph.
- Fulfillment component weights are initial prototype defaults, not an optimized policy.
- Demo order states progress through the simulation clock and are not connected to a delivery partner.
