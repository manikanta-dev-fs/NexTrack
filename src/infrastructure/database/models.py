"""
SQLAlchemy Database Models - With User Authentication

Production-grade ORM models adapted for SQLite with user relationships.
"""

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .config import Base


class TransactionModel(Base):
    """
    Transaction entity in database (with user ownership).
    """
    __tablename__ = "transactions"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User ownership
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Core fields
    description = Column(String(500), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    category = Column(String(50), nullable=False, index=True)
    payment_method = Column(String(20), nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="transactions")
    payment_details = relationship(
        "PaymentDetailModel",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_transaction_user_date', 'user_id', 'created_at'),
        Index('idx_transaction_category_date', 'category', 'created_at'),
        Index('idx_transaction_status_date', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, description={self.description}, amount={self.amount})>"


class PaymentDetailModel(Base):
    """
    Payment details entity.
    """
    __tablename__ = "payment_details"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key
    transaction_id = Column(
        String(36),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Payment info
    payment_type = Column(String(20), nullable=False)
    details = Column(JSON, nullable=False)
    processed_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = relationship("TransactionModel", back_populates="payment_details")
    
    def __repr__(self):
        return f"<PaymentDetail(id={self.id}, type={self.payment_type})>"
