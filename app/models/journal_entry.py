"""Model representing journal entries (double‑entry lines).

Each journal entry belongs to an operation and an account. Debit and credit are
represented as positive numbers (either debit > 0 and credit = 0 or vice versa).
The currency is stored explicitly to support multi‑currency accounting.
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from ..database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    debit = Column(Numeric(18, 2), default=0)
    credit = Column(Numeric(18, 2), default=0)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)

    # Relationships
    operation = relationship("Operation", back_populates="journal_entries")
    account = relationship("Account", back_populates="journal_entries")
    currency = relationship("Currency")

    def __repr__(self) -> str:
        return f"<JournalEntry(op={self.operation_id}, acc={self.account_id}, debit={self.debit}, credit={self.credit})>"