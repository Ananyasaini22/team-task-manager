from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from bson import ObjectId

from config import get_db, JWT_SECRET, JWT_ALGORITHM

bearer_scheme = HTTPBearer()


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises 401 if token is missing, malformed, or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
) -> dict:
    """
    FastAPI dependency — injects the authenticated user document.
    Usage: `user = Depends(get_current_user)`
    """
    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Malformed token")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Attach string id for convenience
    user["id"] = str(user["_id"])
    return user


async def require_project_admin(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """
    Dependency — ensures the current user is an admin of the given project.
    Must be used on routes that have `project_id` as a path parameter.
    """
    from bson import ObjectId as ObjId

    # Project owner always has admin rights
    project = await db.projects.find_one({"_id": ObjId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if str(project["owner_id"]) == current_user["id"]:
        current_user["project_role"] = "admin"
        return current_user

    membership = await db.project_members.find_one({
        "project_id": project_id,
        "user_id":    current_user["id"],
    })
    if not membership or membership.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required for this action",
        )

    current_user["project_role"] = "admin"
    return current_user


async def require_project_member(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """
    Dependency — ensures the current user is at least a member (or owner/admin).
    """
    from bson import ObjectId as ObjId

    project = await db.projects.find_one({"_id": ObjId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Owner always has access
    if str(project["owner_id"]) == current_user["id"]:
        current_user["project_role"] = "admin"
        return current_user

    membership = await db.project_members.find_one({
        "project_id": project_id,
        "user_id":    current_user["id"],
    })
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this project")

    current_user["project_role"] = membership.get("role", "member")
    return current_user
