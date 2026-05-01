from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    todo        = "todo"
    in_progress = "in_progress"
    done        = "done"


class TaskPriority(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


class TaskCreate(BaseModel):
    title:       str          = Field(..., min_length=2, max_length=200)
    description: Optional[str] = ""
    assigned_to: Optional[str] = None   # user_id string
    priority:    TaskPriority  = TaskPriority.medium
    due_date:    Optional[datetime] = None


class TaskUpdate(BaseModel):
    title:       Optional[str]          = None
    description: Optional[str]          = None
    status:      Optional[TaskStatus]   = None
    assigned_to: Optional[str]          = None
    priority:    Optional[TaskPriority] = None
    due_date:    Optional[datetime]     = None


class TaskResponse(BaseModel):
    id:          str
    project_id:  str
    title:       str
    description: str
    status:      TaskStatus
    priority:    TaskPriority
    assigned_to: Optional[str]
    created_by:  str
    due_date:    Optional[datetime]
    created_at:  datetime
    updated_at:  datetime
