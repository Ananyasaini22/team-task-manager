from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    admin  = "admin"
    member = "member"


# ── Request bodies ─────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name:     str       = Field(..., min_length=2, max_length=80)
    email:    EmailStr
    password: str       = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


# ── Database document shape ────────────────────────────────────────────────────

class UserInDB(BaseModel):
    """Represents a user document stored in MongoDB."""
    id:           Optional[str]  = None
    name:         str
    email:        str
    password_hash: str
    created_at:   datetime       = Field(default_factory=datetime.utcnow)


# ── Response (never expose password_hash) ─────────────────────────────────────

class UserResponse(BaseModel):
    id:         str
    name:       str
    email:      str
    created_at: datetime
