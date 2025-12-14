"""Model storing specific details for foreign exchange operations.

For a FX operation we record the amount in USD, the equivalent ARS amount and
whether it was a buy or sell. The exchange rate is stored in the Operation
record.
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Enum
from sqlalchemy.orm import relationship
import enum

from ..database import Base


class FXType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class FXDetail(Base):
    __tablename__ = "fx_details"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False, unique=True)
    usd_amount = Column(Numeric(18, 2), nullable=False)
    ars_amount = Column(Numeric(18, 2), nullable=False)
    fx_type = Column(Enum(FXType), nullable=False)

    # Relationships
    operation = relationship("Operation", back_populates="fx_detail")

    def __repr__(self) -> str:
        return f"<FXDetail(op={self.operation_id}, type={self.fx_type}, usd={self.usd_amount})>"