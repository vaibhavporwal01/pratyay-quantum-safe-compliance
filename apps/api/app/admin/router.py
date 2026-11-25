"""admin: read-only views for the administrator. Users come from identity.service."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.identity import service as identity
from app.identity.deps import User, require_role

router = APIRouter(prefix="/admin", tags=["admin"])

Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[User, Depends(require_role("admin"))]


@router.get("/users")
async def users(session: Session, user: Admin) -> list[dict]:
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "active": u.active,
         "created_at": u.created_at}
        for u in await identity.list_users(session, user.org_id)
    ]
