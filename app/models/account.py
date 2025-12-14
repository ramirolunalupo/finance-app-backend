"""Model representing accounts in the chart of accounts.

Accounts represent financial categories (assets, liabilities, income, expenses).
Additional boolean flags indicate special behaviours (cash/bank accounts, client
accounts, FX result, commission income/expense).
"""

from sqlalchemy import Column, Integer, String, Enum, Boolean
from sqlalchemy.orm import relationship
import enum

from ..database import Base


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    parent_id = Column(Integer, nullable=True)
    # Flags for special behaviour
    is_cash = Column(Boolean, default=False)        # Caja/Banco
    is_client_account = Column(Boolean, default=False)  # Cuentas por cobrar/pagar
    is_fx_result = Column(Boolean, default=False)   # Resultado por tipo de cambio
    is_commission_income = Column(Boolean, default=False)
    is_commission_expense = Column(Boolean, default=False)

    # Relationships
    journal_entries = relationship("JournalEntry", back_populates="account")

    def __repr__(self) -> str:
        return f"<Account(code={self.code}, name={self.name})>"