"""Party management routes placeholder.
Provides CRUD endpoints for clients and suppliers (parties).
"""

from fastapi import APIRouter


router = APIRouter(prefix="/parties", tags=["parties"])

@router.get("/ping")
def ping():
    return {"message": "parties pong"}