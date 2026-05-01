from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from config import connect_db, disconnect_db, get_db
from routes.auth     import router as auth_router
from routes.projects import router as projects_router
from routes.tasks    import router as tasks_router, get_dashboard_data
from middleware.auth_middleware import get_current_user

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Team Task Manager",
    description="REST API for project & task management with role-based access",
    version="1.0.0",
)

# Allow frontend (served from same origin on Railway) + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this to your Railway URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    await connect_db()

@app.on_event("shutdown")
async def on_shutdown():
    await disconnect_db()

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router,     prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tasks_router,    prefix="/api")

# ── Dashboard endpoint ────────────────────────────────────────────────────────

@app.get("/api/dashboard", tags=["Dashboard"])
async def dashboard(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Aggregate task statistics for the logged-in user."""
    return await get_dashboard_data(current_user, db)


# ── Health check (Railway uses this) ─────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Serve frontend static files ───────────────────────────────────────────────
# The frontend/ folder is placed beside backend/ in the repo root.
# We mount it so one Railway service serves both API and UI.

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{page}", include_in_schema=False)
    async def serve_page(page: str):
        file_path = os.path.join(FRONTEND_DIR, f"{page}.html")
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # SPA fallback
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
