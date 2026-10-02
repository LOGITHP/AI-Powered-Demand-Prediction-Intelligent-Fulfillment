from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordRequestForm
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.all_models import User
from app.schemas.all_schemas import Token, UserCreate, UserResponse

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check existing user
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        role=user_in.role,
        store_id=user_in.store_id
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    access_token = create_access_token(
        subject=new_user.email, role=new_user.role, store_id=new_user.store_id
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {"id": new_user.id, "email": new_user.email, "role": new_user.role, "store_id": new_user.store_id}
    }

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        subject=user.email, role=user.role, store_id=user.store_id
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "role": user.role, "store_id": user.store_id}
    }
