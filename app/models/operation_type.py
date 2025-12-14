"""Model representing types of operations.

Examples: FX_BUY, FX_SELL, PAYMENT, RECEIPT, CHEQUE_BUY, CHEQUE_SELL.
"""

from sqlalchemy import Column, Integer, String

from ..database import Base


class OperationType(Base):
    __tablename__ = "operation_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<OperationType(code={self.code})>"