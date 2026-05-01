import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# ── Environment variables ──────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME", "taskmanager")

JWT_SECRET    = os.getenv("JWT_SECRET", "change-this-in-production-please")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES  = 60 * 24        # 1 day
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7   # 7 days

# ── Database client (single shared instance) ──────────────────────────────────
client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """Called on app startup — opens the MongoDB connection."""
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    # Create indexes so lookups stay fast
    await db.users.create_index("email", unique=True)
    await db.tasks.create_index("project_id")
    await db.tasks.create_index("assigned_to")
    await db.project_members.create_index([("project_id", 1), ("user_id", 1)], unique=True)
    print("✅  MongoDB connected and indexes created")


async def disconnect_db():
    """Called on app shutdown — closes the MongoDB connection."""
    global client
    if client:
        client.close()
        print("🔌  MongoDB disconnected")


def get_db():
    """Dependency helper — returns the active database handle."""
    return db
