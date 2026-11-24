from fastapi import APIRouter

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/ping")
async def ping() -> dict:
    return {"module": "rules", "status": "ready"}
