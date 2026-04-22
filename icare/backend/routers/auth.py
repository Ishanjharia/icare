"""Simple file-backed auth (no DB, no JWT — Bearer token is the user email)."""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from deps.auth import get_current_user
from schemas.user import TokenResponse, UserResponse, UserRole
from simple_auth_store import hash_password, load_users, record_to_user_response, save_users

router = APIRouter()


class RegisterData(BaseModel):
    name: str
    email: str
    password: str
    role: str = "patient"
    language: str = "English"
    phone: str = ""


class LoginData(BaseModel):
    email: str
    password: str


def _normalize_role(role: str) -> UserRole:
    try:
        return UserRole(str(role).strip().lower())
    except ValueError:
        return UserRole.patient


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterData) -> UserResponse:
    users = load_users()
    email = str(data.email).strip().lower()
    if email in users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    role = _normalize_role(data.role)
    uid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    phone = (data.phone or "").strip()
    users[email] = {
        "name": data.name.strip(),
        "email": email,
        "password": hash_password(data.password),
        "role": role.value,
        "language": data.language.strip() or "English",
        "phone": phone,
        "id": uid,
        "created_at": now,
    }
    save_users(users)
    return record_to_user_response(users[email])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginData) -> TokenResponse:
    users = load_users()
    email = str(data.email).strip().lower()
    if email not in users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    rec = users[email]
    if rec["password"] != hash_password(data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password")
    user = record_to_user_response(rec)
    return TokenResponse(access_token=email, token_type="bearer", user=user)


@router.get("/me", response_model=UserResponse)
async def read_me(current: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current
