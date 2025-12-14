"""Account management routes placeholder.
In later phases this module will provide endpoints to manage the chart of accounts.
"""

from fastapi import APIRouter


router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/ping")
def ping():
    return {"message": "accounts pong"}