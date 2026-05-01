from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from bson import ObjectId

from config import get_db
from models.task import TaskCreate, TaskUpdate, TaskStatus
from middleware.auth_middleware import get_current_user, require_project_member, require_project_admin
from utils.helpers import doc_to_dict, to_object_id

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])


# ── List tasks in a project ────────────────────────────────────────────────────

@router.get("/")
async def list_tasks(
    project_id: str,
    current_user: dict = Depends(require_project_member),
    db=Depends(get_db),
):
    """Return all tasks for a project. Any project member can view."""
    tasks_cursor = db.tasks.find({"project_id": project_id})
    tasks = await tasks_cursor.to_list(length=500)
    return [doc_to_dict(t) for t in tasks]


# ── Create task (admin only) ───────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_task(
    project_id: str,
    body: TaskCreate,
    current_user: dict = Depends(require_project_admin),
    db=Depends(get_db),
):
    """
    Only project admins can create tasks.
    `assigned_to` must be a valid user_id (member of the project).
    """
    # Validate assigned_to if provided
    if body.assigned_to:
        member = await db.project_members.find_one({
            "project_id": project_id,
            "user_id":    body.assigned_to,
        })
        # Project owner is also valid
        project = await db.projects.find_one({"_id": to_object_id(project_id)})
        if not member and (not project or project["owner_id"] != body.assigned_to):
            raise HTTPException(status_code=400, detail="assigned_to must be a project member")

    now = datetime.utcnow()
    task_doc = {
        "project_id":  project_id,
        "title":       body.title.strip(),
        "description": body.description or "",
        "status":      TaskStatus.todo.value,
        "priority":    body.priority.value,
        "assigned_to": body.assigned_to,
        "created_by":  current_user["id"],
        "due_date":    body.due_date,
        "created_at":  now,
        "updated_at":  now,
    }
    result = await db.tasks.insert_one(task_doc)
    task_doc["_id"] = result.inserted_id
    return doc_to_dict(task_doc)


# ── Get single task ────────────────────────────────────────────────────────────

@router.get("/{task_id}")
async def get_task(
    project_id: str,
    task_id: str,
    current_user: dict = Depends(require_project_member),
    db=Depends(get_db),
):
    task = await db.tasks.find_one({
        "_id":        to_object_id(task_id),
        "project_id": project_id,
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return doc_to_dict(task)


# ── Update task ────────────────────────────────────────────────────────────────

@router.put("/{task_id}")
async def update_task(
    project_id: str,
    task_id: str,
    body: TaskUpdate,
    current_user: dict = Depends(require_project_member),
    db=Depends(get_db),
):
    """
    Role-based update rules:
    - Admin  → can update everything
    - Member → can only update the STATUS of tasks assigned to them
    """
    task = await db.tasks.find_one({
        "_id":        to_object_id(task_id),
        "project_id": project_id,
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    is_admin = current_user.get("project_role") == "admin"

    # Members can only change status, and only for their own tasks
    if not is_admin:
        if task.get("assigned_to") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="Members can only update tasks assigned to them",
            )
        # Strip everything except status
        allowed_updates = {"status": body.status.value if body.status else None}
        updates = {k: v for k, v in allowed_updates.items() if v is not None}
    else:
        updates = {}
        if body.title is not None:        updates["title"]       = body.title.strip()
        if body.description is not None:  updates["description"] = body.description
        if body.status is not None:       updates["status"]      = body.status.value
        if body.assigned_to is not None:  updates["assigned_to"] = body.assigned_to
        if body.priority is not None:     updates["priority"]    = body.priority.value
        if body.due_date is not None:     updates["due_date"]    = body.due_date

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updates["updated_at"] = datetime.utcnow()
    await db.tasks.update_one({"_id": to_object_id(task_id)}, {"$set": updates})
    updated = await db.tasks.find_one({"_id": to_object_id(task_id)})
    return doc_to_dict(updated)


# ── Delete task (admin only) ───────────────────────────────────────────────────

@router.delete("/{task_id}", status_code=204)
async def delete_task(
    project_id: str,
    task_id: str,
    current_user: dict = Depends(require_project_admin),
    db=Depends(get_db),
):
    result = await db.tasks.delete_one({
        "_id":        to_object_id(task_id),
        "project_id": project_id,
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return None


# ── Dashboard summary (global, not scoped to a project) ───────────────────────
# This is mounted separately in main.py under /dashboard

async def get_dashboard_data(current_user: dict, db) -> dict:
    """
    Aggregate stats for the authenticated user:
    - Tasks assigned to them across all projects
    - Count by status
    - Overdue tasks
    """
    uid = current_user["id"]
    now = datetime.utcnow()

    all_tasks = await db.tasks.find({"assigned_to": uid}).to_list(length=1000)

    total      = len(all_tasks)
    todo       = sum(1 for t in all_tasks if t["status"] == "todo")
    in_progress = sum(1 for t in all_tasks if t["status"] == "in_progress")
    done       = sum(1 for t in all_tasks if t["status"] == "done")
    overdue    = sum(
        1 for t in all_tasks
        if t.get("due_date") and t["due_date"] < now and t["status"] != "done"
    )

    recent_tasks = sorted(all_tasks, key=lambda t: t["updated_at"], reverse=True)[:10]

    return {
        "summary": {
            "total":       total,
            "todo":        todo,
            "in_progress": in_progress,
            "done":        done,
            "overdue":     overdue,
        },
        "recent_tasks": [doc_to_dict(t) for t in recent_tasks],
    }
