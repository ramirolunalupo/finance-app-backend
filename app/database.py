"""Database configuration and session management.

This module defines the SQLAlchemy engine and session factory. It reads the
database connection URL from environment variables. If none is provided, it
falls back to an in‑memory SQLite database for development. In production the
connection string should point to a PostgreSQL instance (e.g. Supabase/Neon).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Read the database URL from the environment. Use SQLite for local development.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./finance_app.db")

# SQLAlchemy engine. `connect_args` are required for SQLite.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )
else:
    engine = create_engine(DATABASE_URL)

# Create a configured "Session" class and base class for declarative models.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Provide a transactional scope around a series of operations.

    This function is used as a dependency in FastAPI endpoints to get a
    database session. It will automatically close the session after the
    request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()