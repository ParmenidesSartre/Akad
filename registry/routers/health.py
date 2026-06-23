from fastapi import APIRouter
from sqlalchemy import text
from registry.database import engine

router = APIRouter()


@router.get("/")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "degraded", "db": str(exc)}
