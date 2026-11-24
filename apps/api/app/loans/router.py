import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.identity.deps import User, require_role
from app.loans import service
from app.loans.schemas import ApplicationIn, DecideIn, FactsIn, RecommendIn

router = APIRouter(prefix="/loans", tags=["loans"])

Session = Annotated[AsyncSession, Depends(get_session)]
Applicant = Annotated[User, Depends(require_role("borrower", "officer"))]
Officer = Annotated[User, Depends(require_role("officer"))]
Checker = Annotated[User, Depends(require_role("checker"))]
Anyone = Annotated[User, Depends(require_role("borrower", "officer", "checker", "auditor", "admin"))]
Staff = Annotated[User, Depends(require_role("officer", "checker", "auditor", "admin"))]
Oversight = Annotated[User, Depends(require_role("checker", "auditor", "admin"))]
Auditor = Annotated[User, Depends(require_role("auditor", "admin"))]


def _http(exc: Exception) -> HTTPException:
    match exc:
        case service.NotFound():
            return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
        case service.SameUser():
            return HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        case service.Invalid():
            return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
        case service.LoanError():
            return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    raise exc


async def _detail(session: AsyncSession, user: User, app_id: uuid.UUID) -> dict[str, Any]:
    return await service.detail(session, await service.get_application(session, user, app_id))


@router.get("/products")
async def products(user: Anyone) -> list[dict]:
    return service.list_products()


@router.post("/applications", status_code=status.HTTP_201_CREATED)
async def submit(body: ApplicationIn, session: Session, user: Applicant) -> dict:
    try:
        app = await service.create_application(session, user, body.model_dump())
    except (service.LoanError, service.NotFound) as exc:
        raise _http(exc) from exc
    await session.commit()
    return await service.detail(session, app)


@router.get("/applications")
async def applications(
    session: Session, user: Anyone,
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
) -> list[dict]:
    # Borrowers see only their own (service.list_applications filters on the borrower).
    return await service.list_applications(session, user, tuple(status_) if status_ else None)


@router.get("/applications/{app_id}")
async def application(app_id: uuid.UUID, session: Session, user: Anyone) -> dict:
    try:
        return await _detail(session, user, app_id)
    except service.NotFound as exc:
        raise _http(exc) from exc


async def _act(session: AsyncSession, user: User, app_id: uuid.UUID, action) -> dict:
    try:
        await action()
    except (service.LoanError, service.NotFound) as exc:
        await session.rollback()
        raise _http(exc) from exc
    await session.commit()
    return await _detail(session, user, app_id)


@router.patch("/applications/{app_id}")
async def update(app_id: uuid.UUID, body: FactsIn, session: Session, user: Officer) -> dict:
    return await _act(session, user, app_id, lambda: service.update_facts(
        session, user, app_id, body.model_dump(exclude_unset=True)))


@router.post("/applications/{app_id}/evaluate")
async def evaluate(app_id: uuid.UUID, session: Session, user: Officer) -> dict:
    return await _act(session, user, app_id, lambda: service.reevaluate(session, user, app_id))


@router.post("/applications/{app_id}/recommend")
async def recommend(app_id: uuid.UUID, body: RecommendIn, session: Session, user: Officer):
    return await _act(session, user, app_id, lambda: service.recommend(
        session, user, app_id, body.recommendation, body.amount_paise, body.note))


@router.post("/applications/{app_id}/decide")
async def decide(app_id: uuid.UUID, body: DecideIn, session: Session, user: Checker) -> dict:
    return await _act(session, user, app_id, lambda: service.decide(
        session, user, app_id, body.outcome, body.amount_paise, body.note))


@router.get("/overview")
async def overview(session: Session, user: Staff) -> dict:
    return await service.overview(session, user)


@router.get("/decisions")
async def decisions(session: Session, user: Oversight) -> list[dict]:
    return await service.decisions_log(session, user)


@router.get("/events")
async def events(session: Session, user: Auditor,
                 limit: Annotated[int, Query(ge=1, le=500)] = 100) -> list[dict]:
    return await service.recent_events(session, user, limit)


@router.get("/counts")
async def counts(session: Session, user: Auditor) -> dict:
    return await service.counts(session, user)
