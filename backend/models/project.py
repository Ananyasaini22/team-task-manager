from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name:        str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = ""


class ProjectUpdate(BaseModel):
    name:        Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id:          str
    name:        str
    description: str
    owner_id:    str
    created_at:  datetime


class MemberAdd(BaseModel):
    """Body for adding a member to a project (admin only)."""
    email: str          # look up user by email — friendlier than requiring user_id
    role:  str = "member"   # "admin" | "member"
