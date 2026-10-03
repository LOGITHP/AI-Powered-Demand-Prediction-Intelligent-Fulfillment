import requests
import logging
from sqlalchemy.orm import Session
from app.db.models import Warehouse

logger = logging.getLogger(__name__)

BASE_URL = "http://head-office:8000"
HEADERS = {
    "X-Tunnel-Skip-Antiphishing-Page": "true"
}

def sync_warehouse_status_to_head_office(db: Session, warehouse_id: str = "WH-001"):
    try:
        # 1. Login
        logger.info("Authenticating with Head Office...")
        auth_res = requests.post(
            f"{BASE_URL}/api/auth/login", 
            data={"username": "admin", "password": "admin"},
            headers=HEADERS
        )
        if auth_res.status_code != 200:
            logger.error(f"Failed to authenticate with Head Office: {auth_res.text}")
            return False
            
        token = auth_res.json().get("access_token")
        
        # 2. Get Data
        warehouse = db.query(Warehouse).filter_by(id=warehouse_id).first()
        status = "active" if warehouse else "unknown"

        # 3. Send Data
        logger.info(f"Sending warehouse update for {warehouse_id}...")
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}"
        
        res = requests.post(
            f"{BASE_URL}/api/warehouse-update", 
            json={"warehouse_id": warehouse_id, "status": status}, 
            headers=headers
        )
        if res.status_code == 200:
            logger.info("Successfully synced with Head Office!")
            return True
        else:
            logger.error(f"Failed to sync with Head Office: {res.text}")
            return False
    except Exception as e:
        logger.error(f"Error syncing with head office: {e}")
        return False
