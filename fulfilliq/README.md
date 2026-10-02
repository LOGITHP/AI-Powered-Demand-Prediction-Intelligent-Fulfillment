# FulfillIQ: AI-Powered Inventory Reconciliation and Risk-Aware Fulfillment Platform for Multi-Store Retail Operations

FulfillIQ is a software-first, hardware-independent intelligence layer for multi-store retail operations. It consumes simulated or real operational events, reconciles conflicting inventory observations, estimates current inventory and confidence, predicts discrepancy and fulfillment risk, prioritizes verification, and recommends fulfillment or other operational actions. Its principal differentiation is treating information reliability as a first-class variable in commerce operations.

## 1. Executive Summary

This project proposes a software-first, hardware-independent intelligence layer for a multi-store retailer. The platform does not replace the retailer's ERP, WMS, POS, OMS, e-commerce platform, RFID infrastructure, or IoT systems. Instead, it consumes data from those systems, normalizes events, reconciles conflicting inventory observations, estimates inventory confidence, predicts discrepancy and fulfillment risk, and recommends operational actions.

The central product insight is not "AI can count inventory" or "AI can forecast demand." Major retail platforms already provide capabilities in real-time inventory visibility and order orchestration. The proposed differentiation is a **trust-aware decision layer** that makes uncertainty explicit and uses it in operational decisions.

The prototype can operate without physical RFID readers or IoT devices. A digital-twin-style simulator generates POS, WMS, ERP, e-commerce, RFID-like, sensor, transfer, reservation, and logistics events, including realistic errors such as delays, duplicates, missing events, and conflicting quantities. The hidden simulator state acts as ground truth for evaluation.

## 2. What the Project Is — and Is Not

| Question | Answer |
| --- | --- |
| **Is this another shopping app?** | No. The customer can continue using an existing retailer app. |
| **Is the customer the primary user?** | No. Primary users are retail operations, inventory, and supply-chain teams. |
| **Does it replace SAP/Oracle/WMS/OMS?** | No. It is proposed as a vendor-neutral intelligence layer above existing systems. |
| **Does it count physical inventory itself?** | Not necessarily. It consumes transactions and observations from counting/scanning/RFID systems and estimates reliability. |
| **Does it forecast demand?** | It can, but demand forecasting is not the main innovation. |
| **What is the core AI problem?** | Predicting discrepancy/fulfillment risk and deciding when information is trustworthy enough for action. |
| **Does it require hardware?** | No for the prototype. Real hardware can later feed the same interfaces. |
| **What is the central innovation?** | Trust-aware inventory and fulfillment: state + confidence + risk + action. |

## 3. The Gap We Target

Modern retail already has sophisticated inventory-management systems. The problem FulfillIQ targets is the decision gap created when multiple operational observations are incomplete, delayed, or inconsistent (e.g. POS, WMS, ERP, and RFID reporting different inventory quantities). 

The important question is not only *'which number is correct?'* It is: *'Given the timestamps, source behavior, transaction history, reservations, damage, transfers and observations, what current state should the business trust enough to make a fulfillment decision?'*

**What existing capabilities provide vs. What FulfillIQ adds:**
- **Inventory quantity** ➔ Inventory quantity + confidence/uncertainty
- **Order sourcing** ➔ Order sourcing + information reliability + fulfillment failure risk
- **Stock counting** ➔ Risk-ranked verification priority
- **Correction** ➔ Verified result becomes feedback for future risk models

### Key Innovations
1. **Inventory Confidence Layer** — Estimated state + confidence + evidence.
2. **Discrepancy Risk Prediction** — Probability that inventory state is materially wrong.
3. **Risk-Aware Fulfillment** — Choose fulfillment sources using inventory reliability as a decision variable.
4. **Risk-Ranked Verification** — Prioritize physical checks by risk and business impact.
5. **Value of Verification** — Estimate whether obtaining better information is worth its cost.
6. **Cause-Aware Reconciliation** — Rank likely causes of discrepancies and show evidence.

## 4. Quick start with Docker

Requirements: Docker Desktop with Compose.

1. From this directory, copy `.env.example` to `.env`. Change `JWT_SECRET` before sharing the environment.
2. Start the services:
   ```bash
   docker compose up --build
   ```
3. Open:
   - **Customer and Operations UI**: http://localhost:5173
   - **FastAPI Swagger**: http://localhost:8000/docs
   - **Health API**: http://localhost:8000/health

On first startup, the API creates its schema and seeds 508 products, 50 simulated Coimbatore locations, inventory, inventory events, 30,000 historical order examples, and demo accounts. The initial seed can take a minute. PostgreSQL data is retained in the `postgres_data` volume. Stop with `Ctrl+C`; use `docker compose down` to stop containers.

## 5. Demo Accounts and Suggested Flow

These development-only accounts are seeded automatically. You can also register a Customer, Store Manager, or Admin account directly in the UI.

| Role | Email | Password | Access Level |
| --- | --- | --- | --- |
| Platform admin | admin@fulfilliq.local | FulfillIQ-demo-2026! | Network map, predictions, order queue, simulation tools |
| Store manager | manager01@fulfilliq.local | FulfillIQ-demo-2026! | Store-specific stock, forecasts, recommendations, incoming orders |
| Customer | customer@fulfilliq.local | FulfillIQ-demo-2026! | Customer storefront, browse, order creation |

### Suggested Demo Scenario
1. Create three stores and one distribution center, or use the seeded Coimbatore network.
2. Generate normal POS, WMS, transfer, and reservation events. 
3. Inject a synchronization delay and a missing/duplicate event using the simulation. Show that different sources disagree. 
4. Run reconciliation and show estimated inventory + confidence. 
5. Switch to a Customer account, search for an item, and create an online order. 
6. Compare candidate fulfillment locations and see why the closest location is not necessarily the safest choice based on confidence and discrepancy risk.
7. Recommend a fulfillment source based on the optimization engine.

## 6. Run locally without Docker
Python 3.11+ and Node.js 20+ are recommended. SQLite is the default for local development.

**Backend:**
```powershell
Copy-Item .env.example backend/.env
py -3.11 -m venv backend/venv
.\backend\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Set-Location backend
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```powershell
Set-Location frontend
npm install
npm run dev
```

## 7. Deploy to Render
The repository-root `render.yaml` defines one web service plus a managed PostgreSQL database. The web service builds the React app into the FastAPI image, sharing one public URL.

1. Push this repository to a Git provider connected to Render.
2. In the Render Dashboard, create a new Blueprint and select this repository. 
3. Review the `fulfilliq` web service and `fulfilliq-db` database, then apply the Blueprint. Render generates `JWT_SECRET` and supplies the connection string.
4. Open the web service's `onrender.com` URL when healthy. 

## 8. Technical Architecture & Data Model
FulfillIQ simulates a software-defined digital twin environment because real hardware (RFID, POS machines) is not required for the prototype. It operates via:
- **Simulation**: Python event generation for POS, WMS, delays, and duplicates.
- **API Backend**: FastAPI
- **Database**: PostgreSQL / SQLite (Async SQLAlchemy)
- **ML / AI**: scikit-learn / XGBoost for discrepancy and fulfillment risk.
- **Frontend Dashboard**: React / Vite / Tailwind

The minimal data model tracks:
- `Product`, `Location`, `Order`
- `InventoryEvent` (source, event_type, quantity)
- `InventoryState` (on_hand, reserved, sellable)
- `FulfillmentCandidate` (inventory_estimate, confidence, distance, cost, risk)

## 9. Evidence and Sources
FulfillIQ is informed by leading enterprise capabilities but differentiates on trust-aware decision making:
- [SAP — Unified Commerce Solutions](https://www.sap.com/products/crm/commerce.html)
- [Oracle — Retail Store Inventory Operations Cloud Services](https://docs.oracle.com/en/industries/retail/store-inventory-op-cloud/latest/)
- [Blue Yonder — Inventory Availability](https://blueyonder.com/solutions/order-management-and-commerce/inventory-availability)
- [Manhattan Associates — Store Inventory & Fulfillment](https://www.manh.com/en-in/our-solutions/omnichannel-software-solutions/store-inventory-fulfillment)
- [NIST — Digital Twins](https://www.nist.gov/digital-twins)

*Note: The platform is a "digital-twin-style" simulation prototype and does not represent a certified industrial digital twin or replace core ERP/OMS/WMS systems.*
