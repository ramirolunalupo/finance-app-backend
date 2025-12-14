"""Model storing details of payment operations (yo pago).
Includes gross amount, commission, expenses and payment method.
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from ..database import Base


class PaymentDetail(Base):
    __tablename__ = "payment_details"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False, unique=True)
    gross_amount = Column(Numeric(18, 2), nullable=False)
    commission_amount = Column(Numeric(18, 2), default=0)
    commission_percentage = Column(Numeric(10, 4), nullable=True)
    expenses_amount = Column(Numeric(18, 2), default=0)
    payment_method = Column(String, nullable=True)

    # Relationships
    operation = relationship("Operation", back_populates="payment_detail")

    def __repr__(self) -> str:
        return f"<PaymentDetail(op={self.operation_id}, gross={self.gross_amount})>"