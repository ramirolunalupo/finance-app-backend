"""Entry point for the FastAPI application.

This module initialises the FastAPI app and includes routers for
authentication, CRUD operations and reports. In Phase 1 we focus on
database creation and seeding; the routers will be added in later phases.
"""

from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, parties, operations, reports, accounts


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Finance Operations API", version="0.1.0")

    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Include routers (empty for now; to be implemented in later phases)
    for router in [auth.router, parties.router, operations.router, reports.router, accounts.router]:
        app.include_router(router)

    return app


app = create_app()