"""Model representing high‑level operations.

Each operation has a type (e.g., FX buy/sell, payment, receipt, cheque
purchase/sale), a counterparty, an amount, a currency, a potential exchange rate
and optional notes. Specific details for FX and cheques are stored in separate
tables (fx_details, cheques).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, String
from sqlalchemy.orm import relationship

from ..database import Base


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    operation_type_id = Column(Integer, ForeignKey("operation_types.id"), nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    exchange_rate = Column(Numeric(18, 4), nullable=True)
    notes = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    operation_type = relationship("OperationType")
    party = relationship("Party", back_populates="operations")
    currency = relationship("Currency")
    user = relationship("User", back_populates="operations")
    journal_entries = relationship("JournalEntry", back_populates="operation", cascade="all, delete-orphan")
    fx_detail = relationship("FXDetail", back_populates="operation", uselist=False, cascade="all, delete-orphan")
    cheques = relationship("Cheque", back_populates="operation", cascade="all, delete-orphan")
    payment_detail = relationship("PaymentDetail", back_populates="operation", uselist=False, cascade="all, delete-orphan")
    receipt_detail = relationship("ReceiptDetail", back_populates="operation", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Operation(id={self.id}, type={self.operation_type.code}, date={self.date.date()})>"