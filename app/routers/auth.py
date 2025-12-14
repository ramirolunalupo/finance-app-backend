"""Authentication routes placeholder.

In a later phase, this module will implement user login and token generation.
"""

from fastapi import APIRouter


router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/ping")
def ping():
    return {"message": "auth pong"}