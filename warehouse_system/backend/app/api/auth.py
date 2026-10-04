from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, WorkerPresence
from app.core.security import verify_password, create_access_token
from app.schemas import Token
from datetime import timedelta
from app.core.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("username")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth credentials")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Auto-create hackathon test users if they don't exist
    if not user and form_data.username in ['company', 'deliver', 'manager', 'inbound', 'outbound', 'manager2', 'inbound2', 'outbound2']:
        from app.core.security import get_password_hash
        role = "MANAGER" if "manager" in form_data.username else "WORKER"
        new_user = User(username=form_data.username, hashed_password=get_password_hash(form_data.password), role=role, warehouse_id=settings.WAREHOUSE_ID)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
        
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    # If user is a worker, mark as present
    if user.role == "WORKER":
        from app.db.models import Worker
        worker = db.query(Worker).filter(Worker.user_id == user.id).first()
        if worker:
            worker.status = "ON_SHIFT"
            presence = WorkerPresence(worker_id=worker.worker_id, warehouse_id=user.warehouse_id, shift=worker.shift, status="PRESENT")
            db.add(presence)
            db.commit()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"username": user.username, "role": user.role, "warehouse_id": user.warehouse_id}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "warehouse_id": user.warehouse_id}
