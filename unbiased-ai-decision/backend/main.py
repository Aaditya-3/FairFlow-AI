from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import audit_router, auth_router, health_router


app = FastAPI(title="Unbiased AI Decision", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Unbiased AI Decision backend is running",
        "health_url": "/health",
        "audit_url": "/audit",
    }


app.include_router(health_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(audit_router, tags=["audit"])
