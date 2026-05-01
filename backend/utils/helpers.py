from datetime import datetime, timedelta
from bson import ObjectId
from jose import jwt
from passlib.context import CryptContext

from config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── MongoDB document helpers ───────────────────────────────────────────────────

def doc_to_dict(doc: dict) -> dict:
    """
    Convert a MongoDB document to a plain dict:
    - ObjectId  →  str
    - datetime  →  ISO string (so JSON serialisation never breaks)
    """
    if doc is None:
        return None
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        else:
            result[k] = v
    # Always expose _id as "id"
    if "_id" in result:
        result["id"] = result.pop("_id")
    return result


def to_object_id(id_str: str) -> ObjectId:
    """Parse a string into ObjectId, raising ValueError on bad input."""
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError(f"'{id_str}' is not a valid ObjectId")
