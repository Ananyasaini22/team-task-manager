from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId

from config import get_db
from models.project import ProjectCreate, ProjectUpdate, MemberAdd
from middleware.auth_middleware import get_current_user, require_project_admin, require_project_member
from utils.helpers import doc_to_dict, to_object_id

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── List all projects the current user belongs to ─────────────────────────────

@router.get("/")
async def list_projects(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """
    Returns every project where the user is the owner OR a member.
    We run two queries and merge so owners who haven't been explicitly
    added as members also see their projects.
    """
    uid = current_user["id"]

    # Projects the user owns
    owned_cursor = db.projects.find({"owner_id": uid})
    owned = await owned_cursor.to_list(length=100)

    # Projects where the user is an explicit member
    memberships = await db.project_members.find({"user_id": uid}).to_list(length=200)
    member_project_ids = [ObjectId(m["project_id"]) for m in memberships]

    member_cursor = db.projects.find(
        {"_id": {"$in": member_project_ids}, "owner_id": {"$ne": uid}}
    )
    member_projects = await member_cursor.to_list(length=100)

    all_projects = owned + member_projects
    return [doc_to_dict(p) for p in all_projects]


# ── Create project ─────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Any authenticated user can create a project.
    They automatically become the project's owner (admin-level access).
    """
    doc = {
        "name":        body.name.strip(),
        "description": body.description or "",
        "owner_id":    current_user["id"],
        "created_at":  datetime.utcnow(),
    }
    result = await db.projects.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc_to_dict(doc)


# ── Get single project ─────────────────────────────────────────────────────────

@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(require_project_member),
    db=Depends(get_db),
):
    project = await db.projects.find_one({"_id": to_object_id(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Attach member list for the UI
    members_cursor = db.project_members.find({"project_id": project_id})
    members = await members_cursor.to_list(length=100)

    result = doc_to_dict(project)
    result["members"] = [doc_to_dict(m) for m in members]
    return result


# ── Update project (admin only) ────────────────────────────────────────────────

@router.put("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: dict = Depends(require_project_admin),
    db=Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.utcnow()
    await db.projects.update_one(
        {"_id": to_object_id(project_id)},
        {"$set": updates},
    )
    updated = await db.projects.find_one({"_id": to_object_id(project_id)})
    return doc_to_dict(updated)


# ── Delete project (owner only) ────────────────────────────────────────────────

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(require_project_admin),
    db=Depends(get_db),
):
    project = await db.projects.find_one({"_id": to_object_id(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the project owner can delete it")

    # Cascade delete tasks and memberships
    await db.tasks.delete_many({"project_id": project_id})
    await db.project_members.delete_many({"project_id": project_id})
    await db.projects.delete_one({"_id": to_object_id(project_id)})
    return None


# ── Member management (admin only) ────────────────────────────────────────────

@router.post("/{project_id}/members", status_code=201)
async def add_member(
    project_id: str,
    body: MemberAdd,
    current_user: dict = Depends(require_project_admin),
    db=Depends(get_db),
):
    """Add a user to the project by their email address."""
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'member'")

    target_user = await db.users.find_one({"email": body.email.lower()})
    if not target_user:
        raise HTTPException(status_code=404, detail="No user found with that email")

    target_uid = str(target_user["_id"])

    # Prevent duplicate membership
    existing = await db.project_members.find_one({
        "project_id": project_id,
        "user_id":    target_uid,
    })
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    member_doc = {
        "project_id": project_id,
        "user_id":    target_uid,
        "name":       target_user["name"],
        "email":      target_user["email"],
        "role":       body.role,
        "added_at":   datetime.utcnow(),
    }
    await db.project_members.insert_one(member_doc)
    return doc_to_dict(member_doc)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: str,
    user_id: str,
    current_user: dict = Depends(require_project_admin),
    db=Depends(get_db),
):
    """Remove a member from the project."""
    result = await db.project_members.delete_one({
        "project_id": project_id,
        "user_id":    user_id,
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return None
