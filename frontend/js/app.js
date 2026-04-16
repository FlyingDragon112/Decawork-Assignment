/**
 * IT Admin Panel — Frontend JS
 * Talks to FastAPI backend at API_BASE.
 */

const API_BASE = "http://localhost:8000";

// ── API helpers ──────────────────────────────────────────────────────────

const api = {
  async get(path) {
    const r = await fetch(API_BASE + path);
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },
  async del(path) {
    const r = await fetch(API_BASE + path, { method: "DELETE" });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },
};

// ── Flash messages ───────────────────────────────────────────────────────

function flash(msg, type = "info", duration = 4000) {
  const container = document.getElementById("flash-container");
  const el = document.createElement("div");
  el.className = `flash flash-${type}`;
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  el.innerHTML = `<span>${icons[type] || "ℹ"}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ── Page routing ─────────────────────────────────────────────────────────

function showPage(id) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.getElementById("page-" + id)?.classList.add("active");
  document.querySelector(`[data-page="${id}"]`)?.classList.add("active");

  // update topbar title
  const titles = {
    dashboard: ["Dashboard", "Overview"],
    users:     ["User Management", "All users"],
    "new-user":["Create User", "New account"],
    audit:     ["Audit Log", "Action history"],
  };
  const [title, sub] = titles[id] || ["IT Admin", ""];
  document.getElementById("topbar-title").textContent = title;
  document.getElementById("topbar-sub").textContent = sub;

  // load data
  const loaders = { dashboard: loadDashboard, users: loadUsers, audit: loadAudit };
  loaders[id]?.();
}

// ── Dashboard ─────────────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const data = await api.get("/api/dashboard");
    document.getElementById("stat-total").textContent    = data.stats.total;
    document.getElementById("stat-active").textContent   = data.stats.active;
    document.getElementById("stat-inactive").textContent = data.stats.inactive;

    const tbody = document.getElementById("recent-users-body");
    tbody.innerHTML = data.recent_users.map(u => `
      <tr>
        <td>${u.name}</td>
        <td class="mono" style="color:var(--muted)">${u.email}</td>
        <td>${u.role}</td>
        <td><span class="badge badge-${u.status}">${u.status}</span></td>
      </tr>`).join("");
  } catch (e) {
    flash("Failed to load dashboard: " + e.message, "error");
  }
}

// ── Users ─────────────────────────────────────────────────────────────────

async function loadUsers() {
  const tbody = document.getElementById("users-body");
  tbody.innerHTML = `<tr><td colspan="6" class="empty"><div class="spinner"></div></td></tr>`;
  try {
    const users = await api.get("/api/users");
    document.getElementById("users-count").textContent = users.length;
    if (!users.length) {
      tbody.innerHTML = `<tr><td colspan="6"><div class="empty"><div class="empty-icon">◈</div>No users found.</div></td></tr>`;
      return;
    }
    tbody.innerHTML = users.map(u => `
      <tr>
        <td>${u.name}</td>
        <td class="mono" style="color:var(--muted);font-size:.72rem">${u.email}</td>
        <td>${u.role}</td>
        <td>${u.department}</td>
        <td><span class="badge badge-${u.status}">${u.status}</span></td>
        <td>
          <div class="flex gap-8">
            <button class="btn btn-warn btn-sm" onclick="resetPassword('${u.email}')">Reset PW</button>
            <button class="btn btn-${u.status === 'active' ? 'danger' : 'success'} btn-sm"
                    onclick="toggleStatus('${u.email}')">
              ${u.status === "active" ? "Deactivate" : "Activate"}
            </button>
            <button class="btn btn-ghost btn-sm" onclick="confirmDelete('${u.email}', '${u.name}')">Delete</button>
          </div>
        </td>
      </tr>`).join("");
  } catch (e) {
    flash("Failed to load users: " + e.message, "error");
  }
}

// ── Reset Password ────────────────────────────────────────────────────────

async function resetPassword(email) {
  try {
    const data = await api.post("/api/users/reset-password", { email });
    // show modal with new password
    document.getElementById("pw-email").textContent = email;
    document.getElementById("pw-value").textContent = data.temp_password;
    document.getElementById("pw-modal").classList.add("open");
    flash("Password reset for " + email, "success");
    loadUsers();
  } catch (e) {
    flash("Reset failed: " + e.message, "error");
  }
}

// ── Toggle Status ─────────────────────────────────────────────────────────

async function toggleStatus(email) {
  try {
    const data = await api.post("/api/users/toggle-status", { email });
    flash(`${email}: ${data.old_status} → ${data.new_status}`, "info");
    loadUsers();
  } catch (e) {
    flash("Toggle failed: " + e.message, "error");
  }
}

// ── Delete User ───────────────────────────────────────────────────────────

function confirmDelete(email, name) {
  document.getElementById("del-name").textContent  = name;
  document.getElementById("del-email").textContent = email;
  document.getElementById("del-confirm-btn").onclick = async () => {
    try {
      await api.del(`/api/users/${encodeURIComponent(email)}`);
      flash(`User ${email} deleted`, "success");
      closeModal("delete-modal");
      loadUsers();
    } catch (e) {
      flash("Delete failed: " + e.message, "error");
    }
  };
  document.getElementById("delete-modal").classList.add("open");
}

// ── Create User ───────────────────────────────────────────────────────────

document.getElementById("create-user-form").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = e.target.querySelector("button[type=submit]");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Creating…';

  const body = {
    name:       document.getElementById("new-name").value.trim(),
    email:      document.getElementById("new-email").value.trim(),
    role:       document.getElementById("new-role").value.trim(),
    department: document.getElementById("new-dept").value,
  };

  try {
    const data = await api.post("/api/users", body);
    flash(`User ${body.email} created successfully`, "success");

    // show temp password modal
    document.getElementById("pw-email").textContent = body.email;
    document.getElementById("pw-value").textContent = data.temp_password;
    document.getElementById("pw-modal").classList.add("open");

    e.target.reset();
    showPage("users");
  } catch (err) {
    flash("Create failed: " + err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "Create User";
  }
});

// ── Audit Log ─────────────────────────────────────────────────────────────

async function loadAudit() {
  const tbody = document.getElementById("audit-body");
  tbody.innerHTML = `<tr><td colspan="4" class="empty"><div class="spinner"></div></td></tr>`;
  try {
    const log = await api.get("/api/audit");
    document.getElementById("audit-count").textContent = log.length;
    if (!log.length) {
      tbody.innerHTML = `<tr><td colspan="4"><div class="empty"><div class="empty-icon">◎</div>No audit events yet.</div></td></tr>`;
      return;
    }
    tbody.innerHTML = log.map(e => `
      <tr>
        <td class="mono" style="color:var(--muted);font-size:.7rem;white-space:nowrap">${e.timestamp}</td>
        <td><span class="action-badge action-${e.action}">${e.action}</span></td>
        <td class="mono" style="font-size:.72rem">${e.target}</td>
        <td style="color:var(--muted);font-size:.72rem">${e.details}</td>
      </tr>`).join("");
  } catch (err) {
    flash("Failed to load audit log: " + err.message, "error");
  }
}

// ── Modal helpers ─────────────────────────────────────────────────────────

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

function copyPassword() {
  const pw = document.getElementById("pw-value").textContent;
  navigator.clipboard.writeText(pw).then(() => flash("Password copied!", "success"));
}

// ── Init ──────────────────────────────────────────────────────────────────

showPage("dashboard");