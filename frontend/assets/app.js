/* ================================================================
   app.js  —  Frontend logic for Team Task Manager
   All API calls go through the `api()` helper which injects the JWT.
   State is kept in-memory; localStorage holds only the token + user.
================================================================ */

// ── Config ─────────────────────────────────────────────────────────────────────
const BASE_URL = window.location.origin; // same origin, served by FastAPI

// ── Auth helpers ────────────────────────────────────────────────────────────────
const Auth = {
  getToken:  ()      => localStorage.getItem("ttm_token"),
  getUser:   ()      => JSON.parse(localStorage.getItem("ttm_user") || "null"),
  setSession: (token, user) => {
    localStorage.setItem("ttm_token", token);
    localStorage.setItem("ttm_user", JSON.stringify(user));
  },
  clear: () => {
    localStorage.removeItem("ttm_token");
    localStorage.removeItem("ttm_user");
  },
  isLoggedIn: () => !!localStorage.getItem("ttm_token"),
};

// ── API helper ──────────────────────────────────────────────────────────────────
async function api(path, options = {}) {
  const token = Auth.getToken();
  const res = await fetch(`${BASE_URL}/api${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  // 204 No Content → return null
  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Something went wrong");
  return data;
}

// ── Toast notifications ─────────────────────────────────────────────────────────
function toast(msg, type = "success") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Utility helpers ─────────────────────────────────────────────────────────────
function initials(name) {
  return (name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function isOverdue(due_date, status) {
  if (!due_date || status === "done") return false;
  return new Date(due_date) < new Date();
}

function badgeHtml(value, prefix = "") {
  const cls = prefix ? `badge-${prefix}_${value}` : `badge-${value}`;
  const label = value.replace("_", " ");
  return `<span class="badge ${cls}">${label}</span>`;
}

// ── Modal factory ───────────────────────────────────────────────────────────────
function openModal(title, bodyHtml, footerHtml = "") {
  // Remove any existing modal first
  closeModal();
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "active-modal";
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h2>${title}</h2>
        <button class="modal-close" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
      ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ""}
    </div>`;
  document.body.appendChild(overlay);
}

function closeModal() {
  document.getElementById("active-modal")?.remove();
}

// ── Guard: redirect to login if not authenticated ───────────────────────────────
function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "/";
  }
}

// ── Guard: redirect to dashboard if already authenticated ───────────────────────
function redirectIfAuthed() {
  if (Auth.isLoggedIn()) {
    window.location.href = "/dashboard";
  }
}

// ── Page: Login / Signup ────────────────────────────────────────────────────────
function initAuthPage() {
  redirectIfAuthed();

  const loginTab   = document.getElementById("tab-login");
  const signupTab  = document.getElementById("tab-signup");
  const loginForm  = document.getElementById("form-login");
  const signupForm = document.getElementById("form-signup");

  loginTab.addEventListener("click", () => {
    loginTab.classList.add("active");
    signupTab.classList.remove("active");
    loginForm.classList.remove("hidden");
    signupForm.classList.add("hidden");
  });

  signupTab.addEventListener("click", () => {
    signupTab.classList.add("active");
    loginTab.classList.remove("active");
    signupForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
  });

  // Login submit
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = loginForm.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Signing in…";
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: {
          email:    loginForm.querySelector("#login-email").value,
          password: loginForm.querySelector("#login-password").value,
        },
      });
      Auth.setSession(data.token, data.user);
      window.location.href = "/dashboard";
    } catch (err) {
      showFormError("error-login", err.message);
      btn.disabled = false;
      btn.textContent = "Sign In";
    }
  });

  // Signup submit
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = signupForm.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Creating account…";
    try {
      const data = await api("/auth/signup", {
        method: "POST",
        body: {
          name:     signupForm.querySelector("#signup-name").value,
          email:    signupForm.querySelector("#signup-email").value,
          password: signupForm.querySelector("#signup-password").value,
        },
      });
      Auth.setSession(data.token, data.user);
      window.location.href = "/dashboard";
    } catch (err) {
      showFormError("error-signup", err.message);
      btn.disabled = false;
      btn.textContent = "Create Account";
    }
  });
}

function showFormError(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove("hidden"); }
}

// ── Shared: Sidebar + topbar ────────────────────────────────────────────────────
function renderShell(activePage) {
  const user = Auth.getUser();
  document.getElementById("topbar-user").textContent = user?.name || "User";

  document.getElementById("btn-logout").addEventListener("click", () => {
    Auth.clear();
    window.location.href = "/";
  });

  // Highlight active sidebar link
  document.querySelectorAll(".sidebar a, .sidebar .nav-btn").forEach(el => {
    if (el.dataset.page === activePage) el.classList.add("active");
  });
}

// ── Page: Dashboard ─────────────────────────────────────────────────────────────
async function initDashboardPage() {
  requireAuth();
  renderShell("dashboard");

  try {
    const [dash, projects] = await Promise.all([
      api("/dashboard"),
      api("/projects/"),
    ]);

    // Stats
    const s = dash.summary;
    document.getElementById("stat-total").textContent       = s.total;
    document.getElementById("stat-todo").textContent        = s.todo;
    document.getElementById("stat-inprogress").textContent  = s.in_progress;
    document.getElementById("stat-done").textContent        = s.done;
    document.getElementById("stat-overdue").textContent     = s.overdue;

    // Recent tasks table
    const tbody = document.getElementById("recent-tasks-body");
    if (dash.recent_tasks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;padding:24px">No tasks yet</td></tr>`;
    } else {
      tbody.innerHTML = dash.recent_tasks.map(t => `
        <tr>
          <td>${t.title}</td>
          <td>${badgeHtml(t.status)}</td>
          <td>${badgeHtml(t.priority)}</td>
          <td>${formatDate(t.due_date)}</td>
          <td style="color:${isOverdue(t.due_date, t.status) ? "var(--danger)" : "var(--muted)"}">
            ${isOverdue(t.due_date, t.status) ? "⚠ Overdue" : "On track"}
          </td>
        </tr>`).join("");
    }

    // Projects quick list
    const projList = document.getElementById("project-list");
    if (projects.length === 0) {
      projList.innerHTML = `<p class="text-muted">No projects yet. <a href="/projects">Create one</a></p>`;
    } else {
      projList.innerHTML = projects.slice(0, 5).map(p => `
        <div class="member-item" style="cursor:pointer" onclick="window.location='/project?id=${p.id}'">
          <div class="avatar">${initials(p.name)}</div>
          <div class="member-info">
            <div class="name">${p.name}</div>
            <div class="email">${p.description || "No description"}</div>
          </div>
        </div>`).join("");
    }
  } catch (err) {
    toast(err.message, "error");
  }
}

// ── Page: Projects list ─────────────────────────────────────────────────────────
async function initProjectsPage() {
  requireAuth();
  renderShell("projects");

  async function loadProjects() {
    const grid = document.getElementById("projects-grid");
    grid.innerHTML = `<p class="text-muted">Loading…</p>`;
    try {
      const projects = await api("/projects/");
      if (projects.length === 0) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column:1/-1">
            <div class="icon">📂</div>
            <p>No projects yet. Create your first one!</p>
          </div>`;
      } else {
        grid.innerHTML = projects.map(p => `
          <div class="project-card" onclick="window.location='/project?id=${p.id}'">
            <h3>${p.name}</h3>
            <p>${p.description || "No description"}</p>
            <div class="meta">
              <span class="text-muted" style="font-size:.8rem">Created ${formatDate(p.created_at)}</span>
            </div>
          </div>`).join("");
      }
    } catch (err) {
      toast(err.message, "error");
    }
  }

  loadProjects();

  // Create project modal
  document.getElementById("btn-new-project").addEventListener("click", () => {
    openModal("Create Project",
      `<div class="form-group"><label>Project Name</label><input id="new-proj-name" placeholder="e.g. Website Redesign" /></div>
       <div class="form-group"><label>Description</label><textarea id="new-proj-desc" placeholder="What is this project about?"></textarea></div>
       <div id="new-proj-error" class="alert alert-error hidden"></div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
       <button class="btn btn-primary" onclick="submitCreateProject()">Create</button>`
    );
  });

  window.submitCreateProject = async () => {
    const name = document.getElementById("new-proj-name").value.trim();
    if (!name) { document.getElementById("new-proj-error").textContent = "Name is required"; document.getElementById("new-proj-error").classList.remove("hidden"); return; }
    try {
      await api("/projects/", { method: "POST", body: { name, description: document.getElementById("new-proj-desc").value } });
      closeModal();
      toast("Project created!");
      loadProjects();
    } catch (err) {
      document.getElementById("new-proj-error").textContent = err.message;
      document.getElementById("new-proj-error").classList.remove("hidden");
    }
  };
}

// ── Page: Single Project ────────────────────────────────────────────────────────
async function initProjectPage() {
  requireAuth();
  renderShell("projects");

  const params    = new URLSearchParams(window.location.search);
  const projectId = params.get("id");
  if (!projectId) return window.location.href = "/projects";

  let project = null;
  let tasks   = [];
  let members = [];
  const currentUser = Auth.getUser();

  async function loadAll() {
    try {
      [project, tasks] = await Promise.all([
        api(`/projects/${projectId}`),
        api(`/projects/${projectId}/tasks/`),
      ]);
      members = project.members || [];
      render();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function isAdmin() {
    if (!project) return false;
    if (project.owner_id === currentUser.id) return true;
    const me = members.find(m => m.user_id === currentUser.id);
    return me?.role === "admin";
  }

  function render() {
    document.getElementById("proj-title").textContent = project.name;
    document.getElementById("proj-desc").textContent  = project.description || "";

    // Show admin buttons
    if (isAdmin()) {
      document.getElementById("admin-actions").classList.remove("hidden");
    }

    // Tasks
    const taskBody = document.getElementById("task-body");
    if (tasks.length === 0) {
      taskBody.innerHTML = `<tr><td colspan="6" class="text-muted" style="text-align:center;padding:24px">No tasks yet${isAdmin() ? " — create one above" : ""}</td></tr>`;
    } else {
      taskBody.innerHTML = tasks.map(t => {
        const assignedMember = members.find(m => m.user_id === t.assigned_to);
        const assignedName   = assignedMember ? assignedMember.name : (t.assigned_to ? "Unknown" : "Unassigned");
        const canEdit        = isAdmin() || t.assigned_to === currentUser.id;
        return `
          <tr>
            <td><strong>${t.title}</strong><br><span class="text-muted" style="font-size:.8rem">${t.description || ""}</span></td>
            <td>${badgeHtml(t.status)}</td>
            <td>${badgeHtml(t.priority)}</td>
            <td>${assignedName}</td>
            <td style="color:${isOverdue(t.due_date, t.status) ? "var(--danger)" : "inherit"}">${formatDate(t.due_date)}</td>
            <td>
              ${canEdit ? `<button class="btn btn-sm btn-secondary" onclick="openEditTask('${t.id}')">Edit</button>` : ""}
              ${isAdmin() ? `<button class="btn btn-sm btn-danger" style="margin-left:4px" onclick="deleteTask('${t.id}')">Del</button>` : ""}
            </td>
          </tr>`;
      }).join("");
    }

    // Members
    const memList = document.getElementById("member-list");
    memList.innerHTML = members.map(m => `
      <div class="member-item">
        <div class="avatar">${initials(m.name)}</div>
        <div class="member-info">
          <div class="name">${m.name} ${m.user_id === project.owner_id ? "👑" : ""}</div>
          <div class="email">${m.email}</div>
        </div>
        ${badgeHtml(m.role)}
        ${isAdmin() && m.user_id !== project.owner_id
          ? `<button class="btn btn-sm btn-danger" onclick="removeMember('${m.user_id}')">Remove</button>`
          : ""}
      </div>`).join("") || `<p class="text-muted">No members yet</p>`;
  }

  // ── Create task modal
  window.openCreateTask = () => {
    const memberOptions = members.map(m => `<option value="${m.user_id}">${m.name}</option>`).join("");
    openModal("Create Task",
      `<div class="form-group"><label>Title *</label><input id="t-title" /></div>
       <div class="form-group"><label>Description</label><textarea id="t-desc"></textarea></div>
       <div class="form-group"><label>Assign To</label>
         <select id="t-assign"><option value="">Unassigned</option>${memberOptions}</select></div>
       <div class="form-group"><label>Priority</label>
         <select id="t-priority"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></div>
       <div class="form-group"><label>Due Date</label><input type="date" id="t-due" /></div>
       <div id="t-error" class="alert alert-error hidden"></div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
       <button class="btn btn-primary" onclick="submitCreateTask()">Create</button>`
    );
  };

  window.submitCreateTask = async () => {
    const title = document.getElementById("t-title").value.trim();
    if (!title) { const e = document.getElementById("t-error"); e.textContent = "Title required"; e.classList.remove("hidden"); return; }
    const due   = document.getElementById("t-due").value;
    try {
      await api(`/projects/${projectId}/tasks/`, {
        method: "POST",
        body: {
          title,
          description: document.getElementById("t-desc").value,
          assigned_to: document.getElementById("t-assign").value || null,
          priority:    document.getElementById("t-priority").value,
          due_date:    due ? new Date(due).toISOString() : null,
        },
      });
      closeModal(); toast("Task created!"); loadAll();
    } catch (err) {
      const e = document.getElementById("t-error"); e.textContent = err.message; e.classList.remove("hidden");
    }
  };

  // ── Edit task modal
  window.openEditTask = (taskId) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;
    const admin = isAdmin();
    const statusOpts = ["todo", "in_progress", "done"].map(s =>
      `<option value="${s}" ${task.status === s ? "selected" : ""}>${s.replace("_", " ")}</option>`).join("");
    const memberOptions = members.map(m => `<option value="${m.user_id}" ${task.assigned_to === m.user_id ? "selected" : ""}>${m.name}</option>`).join("");
    const prioOpts = ["low","medium","high"].map(p => `<option value="${p}" ${task.priority === p ? "selected" : ""}>${p}</option>`).join("");

    openModal("Update Task",
      `${admin ? `<div class="form-group"><label>Title</label><input id="et-title" value="${task.title}" /></div>
       <div class="form-group"><label>Description</label><textarea id="et-desc">${task.description || ""}</textarea></div>
       <div class="form-group"><label>Assign To</label><select id="et-assign"><option value="">Unassigned</option>${memberOptions}</select></div>
       <div class="form-group"><label>Priority</label><select id="et-priority">${prioOpts}</select></div>
       <div class="form-group"><label>Due Date</label><input type="date" id="et-due" value="${task.due_date ? task.due_date.slice(0,10) : ""}" /></div>` : ""}
       <div class="form-group"><label>Status</label><select id="et-status">${statusOpts}</select></div>
       <div id="et-error" class="alert alert-error hidden"></div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
       <button class="btn btn-primary" onclick="submitEditTask('${taskId}', ${admin})">Save</button>`
    );
  };

  window.submitEditTask = async (taskId, admin) => {
    const body = { status: document.getElementById("et-status").value };
    if (admin) {
      body.title       = document.getElementById("et-title").value.trim();
      body.description = document.getElementById("et-desc").value;
      body.assigned_to = document.getElementById("et-assign").value || null;
      body.priority    = document.getElementById("et-priority").value;
      const due        = document.getElementById("et-due").value;
      body.due_date    = due ? new Date(due).toISOString() : null;
    }
    try {
      await api(`/projects/${projectId}/tasks/${taskId}`, { method: "PUT", body });
      closeModal(); toast("Task updated!"); loadAll();
    } catch (err) {
      const e = document.getElementById("et-error"); e.textContent = err.message; e.classList.remove("hidden");
    }
  };

  window.deleteTask = async (taskId) => {
    if (!confirm("Delete this task?")) return;
    try {
      await api(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" });
      toast("Task deleted"); loadAll();
    } catch (err) { toast(err.message, "error"); }
  };

  // ── Add member modal
  window.openAddMember = () => {
    openModal("Add Member",
      `<div class="form-group"><label>User Email</label><input id="m-email" type="email" placeholder="member@email.com" /></div>
       <div class="form-group"><label>Role</label>
         <select id="m-role"><option value="member">Member</option><option value="admin">Admin</option></select></div>
       <div id="m-error" class="alert alert-error hidden"></div>`,
      `<button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
       <button class="btn btn-primary" onclick="submitAddMember()">Add</button>`
    );
  };

  window.submitAddMember = async () => {
    try {
      await api(`/projects/${projectId}/members`, {
        method: "POST",
        body: { email: document.getElementById("m-email").value, role: document.getElementById("m-role").value },
      });
      closeModal(); toast("Member added!"); loadAll();
    } catch (err) {
      const e = document.getElementById("m-error"); e.textContent = err.message; e.classList.remove("hidden");
    }
  };

  window.removeMember = async (userId) => {
    if (!confirm("Remove this member?")) return;
    try {
      await api(`/projects/${projectId}/members/${userId}`, { method: "DELETE" });
      toast("Member removed"); loadAll();
    } catch (err) { toast(err.message, "error"); }
  };

  loadAll();
}
