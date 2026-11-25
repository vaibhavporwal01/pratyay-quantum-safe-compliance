"""identity: sign-in, sign-out and the signed-in user (owner: Vishnukant, docs/contracts.md)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.core.config import settings
from app.core.db import get_session
from app.identity import service
from app.identity.deps import SESSION_COOKIE, User, get_current_user, stand_in_enabled

router = APIRouter(prefix="/me", tags=["identity"])
auth_router = APIRouter(prefix="/api/identity", tags=["identity"])

Session = Annotated[AsyncSession, Depends(get_session)]


class MeOut(BaseModel):
    id: str
    org_id: str
    role: str
    name: str
    dev_stand_in: bool


class SignInIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class SignInOut(BaseModel):
    user: MeOut


def _out(user: User | service.User) -> MeOut:
    return MeOut(id=str(user.id), org_id=str(user.org_id), role=user.role, name=user.name,
                 dev_stand_in=stand_in_enabled())


@router.get("", response_model=MeOut)
async def me(user: Annotated[User, Depends(get_current_user)]) -> MeOut:
    return _out(user)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=settings.session_absolute_hours * 3600, path="/",
        httponly=True, samesite="lax", secure=settings.app_env == "production",
    )


@auth_router.post("/sign-in", response_model=SignInOut)
async def sign_in(body: SignInIn, session: Session, response: Response) -> SignInOut:
    result = await service.sign_in(session, body.email, body.password)
    if not result.ok:
        if result.user is not None:
            await audit.log_event(
                session, result.user.id, "sign_in_failed", f"user:{result.user.id}",
                {"locked": result.locked},
            )
        await session.commit()
        # One message for unknown email, wrong password and a locked account.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, service.SIGN_IN_FAILED)
    user = result.user
    await audit.log_event(session, user.id, "sign_in", f"user:{user.id}", {})
    await session.commit()
    _set_cookie(response, result.token)
    return SignInOut(user=_out(user))


@auth_router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(request: Request, session: Session, response: Response) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        user_id = await service.sign_out(session, token)
        if user_id is not None:
            await audit.log_event(session, user_id, "sign_out", f"user:{user_id}", {})
        await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax",
                           secure=settings.app_env == "production")
    return response
