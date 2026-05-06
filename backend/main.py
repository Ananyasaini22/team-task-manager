from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os

from config import connect_db, disconnect_db, get_db
from routes.auth     import router as auth_router
from routes.projects import router as projects_router
from routes.tasks    import router as tasks_router, get_dashboard_data
from middleware.auth_middleware import get_current_user

app = FastAPI(
    title="Team Task Manager",
    description="REST API for project & task management with role-based access",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await connect_db()

@app.on_event("shutdown")
async def on_shutdown():
    await disconnect_db()

app.include_router(auth_router,     prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tasks_router,    prefix="/api")

@app.get("/api/dashboard", tags=["Dashboard"])
async def dashboard(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    return await get_dashboard_data(current_user, db)

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── Debug endpoint — tells us exactly where Railway is looking ────────────────
@app.get("/debug")
async def debug():
    base = os.path.dirname(__file__)
    frontend = os.path.join(base, "frontend")
    return {
        "__file__":       __file__,
        "base_dir":       base,
        "frontend_dir":   frontend,
        "frontend_exists": os.path.isdir(frontend),
        "base_contents":  os.listdir(base),
        "frontend_contents": os.listdir(frontend) if os.path.isdir(frontend) else "NOT FOUND",
    }

# ── Frontend serving ──────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
ASSETS_DIR   = os.path.join(FRONTEND_DIR, "assets")

if os.path.isdir(ASSETS_DIR):
    app.mount("/static", StaticFiles(directory=ASSETS_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    f = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(f):
        return FileResponse(f)
    return HTMLResponse("<h1>Frontend not found</h1><p>Check <a href='/debug'>/debug</a></p>", status_code=404)

@app.get("/{page}", include_in_schema=False)
async def serve_page(page: str):
    # Don't intercept API or static routes
    if page.startswith("api") or page.startswith("static"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    f = os.path.join(FRONTEND_DIR, f"{page}.html")
    if os.path.isfile(f):
        return FileResponse(f)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))