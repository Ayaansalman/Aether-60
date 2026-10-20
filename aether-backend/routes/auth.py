from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from database import get_db
from datetime import datetime, timedelta, timezone
import hashlib
import jwt
import os

router = APIRouter()

JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "aether-dev-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    token: str

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    db = get_db()
    
    # Check if email already exists
    existing = await db["users"].find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    import uuid
    user_id = str(uuid.uuid4())
    display_name = req.display_name or req.email.split("@")[0]
    
    user_doc = {
        "user_id": user_id,
        "email": req.email,
        "password_hash": hash_password(req.password),
        "display_name": display_name,
        "subscription": "pro",
        "created_at": datetime.now(timezone.utc),
        "last_login": datetime.now(timezone.utc),
        "is_verified": True,
    }
    await db["users"].insert_one(user_doc)
    
    token = create_token(user_id, req.email)
    
    return AuthResponse(
        user_id=user_id,
        email=req.email,
        display_name=display_name,
        token=token,
    )

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    db = get_db()
    
    user = await db["users"].find_one({"email": req.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("password_hash") != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update last login
    await db["users"].update_one(
        {"user_id": user["user_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    token = create_token(user["user_id"], user["email"])
    
    return AuthResponse(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user.get("display_name", "Aether User"),
        token=token,
    )
