"""
Pydantic Schemas - Request/Response Validation (Fixed)

Production-grade API schemas with proper discriminated unions.
"""

from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional, Literal, Union


# ============================================================================
# PAYMENT DETAILS SCHEMAS
# ============================================================================

class UPIPaymentDetails(BaseModel):
    """Schema for UPI payment details."""
    upi_id: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$", examples=["user@paytm"])
    app_name: str = Field(..., min_length=1, max_length=50, examples=["Paytm", "GPay"])


class CardPaymentDetails(BaseModel):
    """Schema for card payment details."""
    card_number: str = Field(..., pattern=r"^\d{16}$", examples=["1234567812345678"])
    card_type: Literal["Visa", "Mastercard", "Amex", "Discover"] = Field(..., examples=["Visa"])
    cvv: str = Field(..., pattern=r"^\d{3,4}$", examples=["123"])


# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class TransactionBase(BaseModel):
    """Base schema for transactions."""
    description: str = Field(..., min_length=1, max_length=500, examples=["Grocery shopping"])
    amount: Decimal = Field(..., gt=0, decimal_places=2, examples=[150.50])
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$", examples=["USD", "INR"])
    category: Literal["Food", "Travel", "Bills", "Education", "Shopping", "General"] = Field(..., examples=["Food"])
    payment_method: Literal["upi", "card", "cash", "bank_transfer"] = Field(..., examples=["upi"])


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    payment_details: Union[UPIPaymentDetails, CardPaymentDetails, dict] = Field(..., examples=[{
        "upi_id": "user@paytm",
        "app_name": "Paytm"
    }])


class TransactionResponse(TransactionBase):
    """Schema for transaction responses."""
    id: str  # UUID as string for SQLite
    status: Literal["pending", "completed", "failed", "cancelled"]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TransactionUpdate(BaseModel):
    """Schema for updating transactions."""
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[Literal["Food", "Travel", "Bills", "Education", "Shopping", "General"]] = None
    status: Optional[Literal["pending", "completed", "failed", "cancelled"]] = None


# ============================================================================
# LIST AND PAGINATION SCHEMAS
# ============================================================================

class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list."""
    total: int = Field(..., ge=0, examples=[100])
    page: int = Field(..., ge=1, examples=[1])
    page_size: int = Field(..., ge=1, le=100, examples=[10])
    transactions: list[TransactionResponse]


class PaginationParams(BaseModel):
    """Reusable pagination parameters."""
    page: int = Field(default=1, ge=1, examples=[1])
    page_size: int = Field(default=10, ge=1, le=100, examples=[10])


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class CategoryStats(BaseModel):
    """Statistics for a single category."""
    count: int = Field(..., ge=0)
    total: Decimal = Field(..., ge=0)
    average: Decimal = Field(..., ge=0)


class StatisticsResponse(BaseModel):
    """Schema for transaction statistics."""
    total_transactions: int = Field(..., ge=0, examples=[150])
    total_amount: Decimal = Field(..., ge=0, examples=[Decimal("5000.00")])
    by_category: dict[str, CategoryStats]
    by_payment_method: dict[str, int]
    date_range: Optional[dict[str, datetime]] = None


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., examples=["Transaction not found"])
    error_code: Optional[str] = Field(None, examples=["TRANSACTION_NOT_FOUND"])


# ============================================================================
# HEALTH CHECK SCHEMA
# ============================================================================

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: Literal["healthy", "unhealthy"]
    service: str = "NexTrack API"
    version: str = "2.0.0"
    database: Optional[Literal["connected", "disconnected"]] = None
