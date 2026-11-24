from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.health import router as health_router
from app.identity.deps import dev_role_middleware
from app.identity.router import router as identity_router
from app.rules.router import router as rules_router

app = FastAPI(title="Pratyay API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(dev_role_middleware)
app.include_router(health_router)
app.include_router(identity_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
