"""Model to represent currencies.

Each currency has an ISO code (e.g. ARS, USD) and a descriptive name.
"""

from sqlalchemy import Column, Integer, String

from ..database import Base


class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, nullable=False)
    name = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Currency(code={self.code})>"