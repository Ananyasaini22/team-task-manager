# TaskFlow — Team Task Manager

A full-stack web application for creating projects, managing teams, assigning tasks, and tracking progress with role-based access control.

## Live Demo

> Add your Railway URL here after deployment

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11 + FastAPI |
| Database | MongoDB Atlas (via async `motor` driver) |
| Auth | JWT (JSON Web Tokens) + bcrypt |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Deployment | Railway |

---

## Features

### Authentication
- Signup / Login with email + password
- Passwords hashed with bcrypt — never stored in plain text
- JWT issued on login, validated on every protected request
- Unified error message for invalid credentials (prevents email enumeration)

### Projects
- Any user can create a project; they become its owner (admin)
- List all projects you own or are a member of
- Update and delete projects (admin only; delete cascades tasks and memberships)

### Team Management (Role-Based Access Control)
Two roles exist per project:

| Action | Admin | Member |
|--------|-------|--------|
| View project & tasks | ✅ | ✅ |
| Create tasks | ✅ | ❌ |
| Edit any task field | ✅ | ❌ |
| Update status of own tasks | ✅ | ✅ |
| Delete tasks | ✅ | ❌ |
| Add / remove members | ✅ | ❌ |

### Tasks
- Create with title, description, priority (low/medium/high), assignee, due date
- Status tracking: `todo → in_progress → done`
- Overdue detection (due date passed and not done)

### Dashboard
- Aggregated stats: total tasks, by status, overdue count
- 10 most recently updated tasks assigned to you

---

## Project Structure

```
team-task-manager/
├── backend/
│   ├── main.py                 # FastAPI app, routes, static file serving
│   ├── config.py               # MongoDB connection + JWT config
│   ├── models/
│   │   ├── user.py             # Pydantic models for users
│   │   ├── project.py          # Pydantic models for projects
│   │   └── task.py             # Pydantic models for tasks
│   ├── routes/
│   │   ├── auth.py             # POST /auth/signup, /auth/login, GET /auth/me
│   │   ├── projects.py         # CRUD for projects + member management
│   │   └── tasks.py            # CRUD for tasks + dashboard aggregation
│   ├── middleware/
│   │   └── auth_middleware.py  # JWT verification, RBAC dependencies
│   ├── utils/
│   │   └── helpers.py          # Password hashing, JWT creation, doc conversion
│   └── requirements.txt
├── frontend/
│   ├── index.html              # Login / Signup
│   ├── dashboard.html          # Stats + recent tasks
│   ├── projects.html           # Project list
│   ├── project.html            # Single project: tasks + members
│   └── assets/
│       ├── style.css
│       └── app.js              # All frontend logic
├── nixpacks.toml               # Railway build config
├── railway.toml                # Railway deploy config
├── .env.example
└── .gitignore
```

---

## REST API Reference

### Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/signup` | None | Register new user |
| POST | `/api/auth/login` | None | Login, get JWT |
| GET | `/api/auth/me` | JWT | Get own profile |

### Projects
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/api/projects/` | Member | List my projects |
| POST | `/api/projects/` | Any | Create project |
| GET | `/api/projects/{id}` | Member | Get project + members |
| PUT | `/api/projects/{id}` | Admin | Update project |
| DELETE | `/api/projects/{id}` | Owner | Delete project + cascade |
| POST | `/api/projects/{id}/members` | Admin | Add member by email |
| DELETE | `/api/projects/{id}/members/{uid}` | Admin | Remove member |

### Tasks
| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/api/projects/{id}/tasks/` | Member | List tasks |
| POST | `/api/projects/{id}/tasks/` | Admin | Create task |
| GET | `/api/projects/{id}/tasks/{tid}` | Member | Get task |
| PUT | `/api/projects/{id}/tasks/{tid}` | Member* | Update task |
| DELETE | `/api/projects/{id}/tasks/{tid}` | Admin | Delete task |

*Members can only update `status` on tasks assigned to them.

### Dashboard
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard` | JWT | Task stats + recent tasks |

Interactive API docs available at `/docs` (Swagger UI) when running locally.

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- A free MongoDB Atlas account (or local MongoDB)

### Steps

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd team-task-manager

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your MongoDB URI and a JWT secret

# 5. Run the server
cd backend
uvicorn main:app --reload --port 8000

# 6. Visit http://localhost:8000
```

Generate a JWT secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deployment on Railway

### 1. Set up MongoDB Atlas
1. Create a free account at [mongodb.com](https://www.mongodb.com/cloud/atlas)
2. Create a free M0 cluster
3. Create a database user (Settings → Database Access)
4. Whitelist all IPs: `0.0.0.0/0` (Network Access)
5. Copy your connection string

### 2. Deploy to Railway
1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Select your repository
4. Go to **Variables** tab and add:
   ```
   MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
   DB_NAME=taskmanager
   JWT_SECRET=your-long-random-secret
   ```
5. Railway will auto-detect the `nixpacks.toml` and build + deploy

### 3. Get your URL
Railway assigns a public URL like `https://your-app.up.railway.app`

---

## Database Design

### Collections

**users**
```json
{ "_id": ObjectId, "name": str, "email": str (unique), "password_hash": str, "created_at": datetime }
```

**projects**
```json
{ "_id": ObjectId, "name": str, "description": str, "owner_id": str, "created_at": datetime }
```

**project_members**
```json
{ "_id": ObjectId, "project_id": str, "user_id": str, "name": str, "email": str, "role": "admin"|"member", "added_at": datetime }
```
*Unique index on (project_id, user_id)*

**tasks**
```json
{ "_id": ObjectId, "project_id": str, "title": str, "description": str, "status": "todo"|"in_progress"|"done", "priority": "low"|"medium"|"high", "assigned_to": str|null, "created_by": str, "due_date": datetime|null, "created_at": datetime, "updated_at": datetime }
```

---

## Security Considerations

- Passwords are hashed with bcrypt (cost factor 12)
- JWT tokens expire after 24 hours
- RBAC enforced server-side on every request — the frontend just shows/hides UI
- Same error message for "wrong password" and "email not found" (prevents enumeration)
- MongoDB indexes on unique fields prevent duplicates at the database level

---

## Author

Built as part of a full-stack engineering assignment.
