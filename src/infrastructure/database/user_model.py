"""
User Model and Authentication

SQLAlchemy model for users with password hashing.
"""

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from passlib.context import CryptContext
import uuid

from .config import Base

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserModel(Base):
    """User entity for authentication."""
    __tablename__ = "users"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User credentials
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # User info
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "admin" or "user"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    transactions = relationship(
        "TransactionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def verify_password(self, plain_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, self.hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password."""
        return pwd_context.hash(password)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
