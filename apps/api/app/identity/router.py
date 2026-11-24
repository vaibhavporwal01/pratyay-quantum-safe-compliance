"""identity: the signed-in user, for the web masthead. Stand-in until Vishnukant's module."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.identity.deps import User, get_current_user

router = APIRouter(prefix="/me", tags=["identity"])


class MeOut(BaseModel):
    id: str
    org_id: str
    role: str
    name: str
    dev_stand_in: bool


@router.get("", response_model=MeOut)
async def me(user: Annotated[User, Depends(get_current_user)]) -> MeOut:
    return MeOut(
        id=str(user.id), org_id=str(user.org_id), role=user.role, name=user.name,
        dev_stand_in=settings.app_env == "development",
    )
