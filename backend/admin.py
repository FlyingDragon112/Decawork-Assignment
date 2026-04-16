"""
IT Admin Panel — FastAPI Backend
Pure JSON REST API. Frontend is served separately from /frontend/.

Run:
    pip install fastapi uvicorn
    uvicorn admin:app --reload --port 8000
"""

from __future__ import annotations

import hashlib
import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

USERS: dict[str, dict] = {
    "john@company.com": {
        "name": "John Smith",
        "email": "john@company.com",
        "role": "Engineer",
        "department": "Engineering",
        "status": "active",
        "password_hash": hashlib.sha256(b"pass1234").hexdigest(),
        "created_at": "2024-01-15",
    },
    "sarah@company.com": {
        "name": "Sarah Connor",
        "email": "sarah@company.com",
        "role": "Manager",
        "department": "Operations",
        "status": "active",
        "password_hash": hashlib.sha256(b"pass5678").hexdigest(),
        "created_at": "2024-02-20",
    },
    "mike@company.com": {
        "name": "Mike Johnson",
        "email": "mike@company.com",
        "role": "Analyst",
        "department": "Finance",
        "status": "inactive",
        "password_hash": hashlib.sha256(b"pass9999").hexdigest(),
        "created_at": "2024-03-10",
    },
}

AUDIT_LOG: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(action: str, target: str, details: str = "") -> None:
    AUDIT_LOG.insert(
        0,
        {
            "id": len(AUDIT_LOG) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "target": target,
            "details": details,
        },
    )


def _gen_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="IT Admin API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    name: str
    email: str
    role: str
    department: str


class ResetPasswordRequest(BaseModel):
    email: str


class ToggleStatusRequest(BaseModel):
    email: str


class DeleteUserRequest(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
async def dashboard():
    total = len(USERS)
    active = sum(1 for u in USERS.values() if u["status"] == "active")
    recent = list(USERS.values())[-5:]
    return {
        "stats": {
            "total": total,
            "active": active,
            "inactive": total - active,
        },
        "recent_users": recent,
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@app.get("/api/users")
async def list_users():
    return list(USERS.values())


@app.get("/api/users/{email}")
async def get_user(email: str):
    if email not in USERS:
        raise HTTPException(status_code=404, detail=f"User {email} not found")
    return USERS[email]


@app.post("/api/users", status_code=201)
async def create_user(body: CreateUserRequest):
    if body.email in USERS:
        raise HTTPException(status_code=409, detail=f"User {body.email} already exists")
    temp_pw = _gen_password()
    USERS[body.email] = {
        "name": body.name,
        "email": body.email,
        "role": body.role,
        "department": body.department,
        "status": "active",
        "password_hash": hashlib.sha256(temp_pw.encode()).hexdigest(),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    _log("CREATE_USER", body.email, f"name={body.name}, role={body.role}, dept={body.department}")
    return {"message": f"User {body.email} created", "temp_password": temp_pw, "user": USERS[body.email]}


@app.post("/api/users/reset-password")
async def reset_password(body: ResetPasswordRequest):
    if body.email not in USERS:
        raise HTTPException(status_code=404, detail=f"User {body.email} not found")
    new_pw = _gen_password()
    USERS[body.email]["password_hash"] = hashlib.sha256(new_pw.encode()).hexdigest()
    _log("RESET_PASSWORD", body.email, f"new_temp_password={new_pw}")
    return {"message": f"Password reset for {body.email}", "temp_password": new_pw}


@app.post("/api/users/toggle-status")
async def toggle_status(body: ToggleStatusRequest):
    if body.email not in USERS:
        raise HTTPException(status_code=404, detail=f"User {body.email} not found")
    old = USERS[body.email]["status"]
    new = "inactive" if old == "active" else "active"
    USERS[body.email]["status"] = new
    _log("TOGGLE_STATUS", body.email, f"{old} → {new}")
    return {"message": f"Status updated for {body.email}", "old_status": old, "new_status": new}


@app.delete("/api/users/{email}")
async def delete_user(email: str):
    if email not in USERS:
        raise HTTPException(status_code=404, detail=f"User {email} not found")
    del USERS[email]
    _log("DELETE_USER", email)
    return {"message": f"User {email} deleted"}


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

@app.get("/api/audit")
async def audit_log():
    return AUDIT_LOG


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("admin:app", host="0.0.0.0", port=8000, reload=True)