"""Model for counterparties (clients or providers).

The `Party` table stores information about clients and providers.
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..database import Base


class PartyType(str, enum.Enum):
    CLIENT = "client"
    SUPPLIER = "supplier"


class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(PartyType), default=PartyType.CLIENT)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    operations = relationship("Operation", back_populates="party")

    def __repr__(self) -> str:
        return f"<Party(id={self.id}, name={self.name})>"