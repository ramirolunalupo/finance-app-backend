"""Operations routes placeholder.
Will include endpoints to create FX, payment, receipt and cheque operations.
"""

from fastapi import APIRouter


router = APIRouter(prefix="/operations", tags=["operations"])

@router.get("/ping")
def ping():
    return {"message": "operations pong"}