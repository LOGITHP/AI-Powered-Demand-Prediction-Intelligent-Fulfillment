# FulfillIQ Prototype

An intelligent retail and fulfillment infrastructure platform prototype predicting product availability and demand.

## Requirements
- Docker and Docker Compose
- (Optional) Node 18+ and Python 3.11+ for local non-docker execution

## Quick Start (Dockerized)

1. **Start the platform**
   ```bash
   docker-compose up -d --build
   ```

2. **Wait for services to initialize**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - Swagger Docs: http://localhost:8000/docs

3. **Generate Seed Data**
   Since the database is empty on first boot, you need to populate it. 
   Enter the backend container and run the data generator script:
   ```bash
   docker exec -it fulfilliq-backend bash
   python scripts/generate_data.py
   exit
   ```

## Seed Accounts
Once the data is generated, you can login via the frontend (http://localhost:5173/login) using these credentials:

- **Platform Admin**: `admin@fulfilliq.local` / `admin123`
- **Store Manager**: `manager01@fulfilliq.local` / `manager123`
- **Customer**: `customer@fulfilliq.local` / `customer123`

## Features and Workflows
1. **Customer**: Browse products, view availability confidence for nearby stores, place simulated orders.
2. **Store Manager**: Monitor local inventory, view localized demand predictions, receive FulfillIQ inventory actions (transfer/replenish).
3. **Platform Admin**: View city-wide store statuses, monitor 100k+ historical orders, and train the Machine Learning Models (Demand and Availability).
