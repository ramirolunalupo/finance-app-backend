"""Model representing cheque details for buy/sell operations.

Each cheque belongs to an operation and contains specific financial details.
"""

from datetime import date
from sqlalchemy import Column, Integer, ForeignKey, Numeric, Date, String, Enum
from sqlalchemy.orm import relationship
import enum

from ..database import Base


class ChequeStatus(str, enum.Enum):
    PENDING = "pending"
    ACCREDITED = "accredited"
    EXPIRED = "expired"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Cheque(Base):
    __tablename__ = "cheques"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    bank = Column(String, nullable=False)
    number = Column(String, nullable=False)
    nominal_amount = Column(Numeric(18, 2), nullable=False)
    issue_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=False)
    expected_accreditation_date = Column(Date, nullable=True)
    interest_rate = Column(Numeric(10, 4), nullable=True)  # annual rate
    interest_base = Column(Integer, default=365)  # base days for calculation
    expenses = Column(Numeric(18, 2), default=0)
    commissions = Column(Numeric(18, 2), default=0)
    net_amount = Column(Numeric(18, 2), nullable=True)
    status = Column(Enum(ChequeStatus), default=ChequeStatus.PENDING, index=True)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)

    # Relationships
    operation = relationship("Operation", back_populates="cheques")
    currency = relationship("Currency")
    party = relationship("Party")

    def __repr__(self) -> str:
        return f"<Cheque(id={self.id}, number={self.number}, status={self.status})>"