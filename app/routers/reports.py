"""Report routes placeholder.
Will provide endpoints for positions, client ledgers and cheque listings.
"""

from fastapi import APIRouter


router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/ping")
def ping():
    return {"message": "reports pong"}