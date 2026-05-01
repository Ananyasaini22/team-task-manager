from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from config import get_db
from models.user import SignupRequest, LoginRequest
from utils.helpers import hash_password, verify_password, create_access_token, doc_to_dict
from middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", status_code=201)
async def signup(body: SignupRequest, db=Depends(get_db)):
    """
    Register a new user.
    - Email must be unique.
    - Password is bcrypt-hashed before storage — never stored in plain text.
    """
    # Check for duplicate email
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user_doc = {
        "name":          body.name.strip(),
        "email":         body.email.lower(),
        "password_hash": hash_password(body.password),
        "created_at":    datetime.utcnow(),
    }
    result = await db.users.insert_one(user_doc)
    token   = create_access_token(str(result.inserted_id))

    return {
        "message": "Account created successfully",
        "token":   token,
        "user": {
            "id":    str(result.inserted_id),
            "name":  user_doc["name"],
            "email": user_doc["email"],
        },
    }


@router.post("/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    """
    Authenticate with email + password.
    Returns a JWT on success.
    """
    user = await db.users.find_one({"email": body.email.lower()})

    # Use same error message for both "not found" and "wrong password"
    # to avoid leaking which emails are registered (security best practice)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user["_id"]))
    return {
        "token": token,
        "user": {
            "id":    str(user["_id"]),
            "name":  user["name"],
            "email": user["email"],
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return doc_to_dict(current_user)
