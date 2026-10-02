# FulfillIQ architecture

## Request flow

The React customer screen sends product, requested quantity and coordinates to FastAPI. The backend filters nearby simulated stores, reads inventory, estimates hourly demand and availability probability, calculates a weighted fulfillment score and returns the best candidate with alternatives and reasons. Placing a demo order validates the selected inventory again, reduces on-hand units and records an inventory sale event.

## Services

- frontend: React, TypeScript, React Router, TanStack Query, React Hook Form, Zod, Tailwind CSS, Recharts and Leaflet.
- backend: FastAPI REST API, Pydantic validation, SQLAlchemy async database access and JWT bearer authentication.
- database: PostgreSQL in Docker Compose; SQLite through aiosqlite for local development.
- model storage: Joblib Random Forest artifacts and model-version metadata in the database.

## Roles

Public registration assigns CUSTOMER only. Store managers are assigned to one store by the seed account. Manager API operations apply a store-id check. Model training, activation, data generation, transfers, map and global analytics require PLATFORM_ADMIN. Product browsing and recommendation calculation can be viewed without signing in; placing an order requires a customer token.

## Prediction and scoring

Before a model is trained and activated, hourly demand uses a category/daypart/weekday baseline. Availability blends stock sufficiency with inventory accuracy and update freshness. The main score uses configurable prototype defaults: availability 40%, inventory adequacy 20%, estimated distance 20%, future availability 10%, and delivery feasibility 10%. The components and reasons are included in the recommendation response.

The train endpoints fit Random Forest models on generated historical orders, evaluate an 80/20 holdout and save Joblib model files. Model metrics refer only to this generated dataset. The business comparison samples historical outcomes and uses present inventory for alternative-store estimates; it is a demonstrator, not a causal production experiment.

## Seed and migration lifecycle

At startup, SQLAlchemy creates missing tables. If the store table is empty, the seed service creates the fictional Coimbatore network, 508 products, inventory and inventory events, 30,000 demand-sensitive historical order examples, demo users and a store recommendation. Re-running startup leaves an existing dataset intact. Alembic provides an initial schema migration; migrations do not seed or reset data.
