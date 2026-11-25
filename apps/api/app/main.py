from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.router import router as admin_router
from app.core.config import settings
from app.core.csrf import csrf_middleware
from app.core.health import router as health_router
from app.identity.deps import identity_cookie_middleware
from app.identity.router import auth_router
from app.identity.router import router as identity_router
from app.loans.router import router as loans_router
from app.rules.router import router as rules_router

app = FastAPI(title="Pratyay API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(identity_cookie_middleware)
app.middleware("http")(csrf_middleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(identity_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(loans_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
