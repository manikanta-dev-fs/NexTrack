"""
NexTrack Domain Models - Day 3: OOP & SOLID Principles (Refactored)

Architectural Patterns:
- Domain-Driven Design (DDD): Transaction and Payment as domain entities
- Factory Pattern: PaymentFactory for object creation
- Repository Pattern: Separation of domain logic from persistence
- Dependency Injection: Loose coupling between components

Interview Talking Points:
"I designed this using SOLID principles. Each class has a single responsibility,
and I use dependency injection to make the code testable and maintainable."
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal  # Use Decimal for financial calculations (IEEE 754 precision issues)
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import uuid4
import re


# ============================================================================
# DOMAIN ENUMS (Type Safety)
# ============================================================================

class PaymentMethod(Enum):
    """Payment method types (Open/Closed Principle: Easy to extend)."""
    UPI = "upi"
    CARD = "card"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"


class TransactionStatus(Enum):
    """Transaction lifecycle states (State Machine Pattern)."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# PROTOCOLS (Interface Segregation Principle)
# ============================================================================

@runtime_checkable
class Payable(Protocol):
    """
    Protocol for payment processing (Duck Typing with Type Safety).
    
    Interview Talking Point:
    "I use Protocols instead of abstract base classes when I want structural
    subtyping. This is more flexible and follows Python's duck typing philosophy."
    """
    
    def process_payment(self) -> dict[str, bool | str]:
        """Process the payment and return result."""
        ...
    
    def get_receipt(self) -> str:
        """Generate payment receipt."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for validation logic."""
    
    def validate(self) -> dict[str, bool | str]:
        """Validate the entity."""
        ...


# ============================================================================
# VALUE OBJECTS (DDD Pattern: Immutable, Identity-less)
# ============================================================================

@dataclass(frozen=True)
class Money:
    """
    Value Object for monetary amounts (Domain-Driven Design).
    
    Architectural Why:
    - Uses Decimal for precision (no floating-point errors)
    - Immutable (thread-safe)
    - Type-safe (can't accidentally add Money + int)
    
    Interview Answer:
    "I use the Money pattern to encapsulate currency logic and prevent
    floating-point precision errors in financial calculations."
    """
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        """Validate after initialization."""
        if self.amount < 0:
            raise ValueError(f"Amount cannot be negative: {self.amount}")
        if not isinstance(self.amount, Decimal):
            # Convert to Decimal if needed
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
    
    def __add__(self, other: 'Money') -> 'Money':
        """Add two Money objects (same currency only)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"


@dataclass(frozen=True)
class UPIDetails:
    """Value Object for UPI payment details."""
    upi_id: str
    app_name: str
    
    def __post_init__(self):
        """Validate UPI ID format."""
        pattern = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$'
        if not re.match(pattern, self.upi_id):
            raise ValueError(f"Invalid UPI ID format: {self.upi_id}")


@dataclass(frozen=True)
class CardDetails:
    """Value Object for card payment details."""
    card_number: str
    card_type: str
    cvv: str = field(repr=False)  # Don't print CVV in logs
    
    def __post_init__(self):
        """Validate card details."""
        clean_number = self.card_number.replace(" ", "")
        if len(clean_number) != 16 or not clean_number.isdigit():
            raise ValueError("Card number must be 16 digits")
        if len(self.cvv) not in (3, 4) or not self.cvv.isdigit():
            raise ValueError("CVV must be 3 or 4 digits")
    
    @property
    def masked_number(self) -> str:
        """Return masked card number for security."""
        return "*" * 12 + self.card_number[-4:]


# ============================================================================
# DOMAIN ENTITIES (DDD Pattern: Have Identity)
# ============================================================================

@dataclass
class Transaction:
    """
    Transaction Entity (Aggregate Root in DDD).
    
    Architectural Pattern: Aggregate Root
    - Encapsulates business rules
    - Maintains consistency boundaries
    - Has unique identity (UUID)
    
    Interview Talking Point:
    "Transaction is an aggregate root that ensures all business rules are
    enforced. It can't be created in an invalid state thanks to validation
    in the constructor."
    """
    description: str
    amount: Money
    category: str
    payment_method: PaymentMethod
    id: str = field(default_factory=lambda: str(uuid4()))
    status: TransactionStatus = TransactionStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate transaction on creation (Fail Fast Principle)."""
        validation = self.validate()
        if not validation["success"]:
            raise ValueError(validation["error"])
    
    def validate(self) -> dict[str, bool | str]:
        """
        Validate transaction business rules.
        
        Pro-Tip: Centralize validation logic in the entity itself.
        """
        if not self.description.strip():
            return {"success": False, "error": "Description cannot be empty"}
        
        if self.amount.amount <= 0:
            return {"success": False, "error": "Amount must be positive"}
        
        return {"success": True, "message": "Valid transaction"}
    
    def complete(self) -> None:
        """Mark transaction as completed (State Transition)."""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot complete transaction in {self.status} state")
        self.status = TransactionStatus.COMPLETED
    
    def cancel(self) -> None:
        """Cancel the transaction."""
        if self.status == TransactionStatus.COMPLETED:
            raise ValueError("Cannot cancel completed transaction")
        self.status = TransactionStatus.CANCELLED
    
    def to_dict(self) -> dict:
        """Serialize to dictionary (for JSON storage)."""
        return {
            "id": self.id,
            "description": self.description,
            "amount": float(self.amount.amount),
            "currency": self.amount.currency,
            "category": self.category,
            "payment_method": self.payment_method.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


# ============================================================================
# PAYMENT IMPLEMENTATIONS (Strategy Pattern)
# ============================================================================

class BasePayment(ABC):
    """
    Abstract base class for payments (Template Method Pattern).
    
    Architectural Why: Defines the skeleton of payment processing,
    allowing subclasses to override specific steps.
    """
    
    def __init__(self, transaction: Transaction):
        """Initialize with transaction reference."""
        self.transaction = transaction
        self.processed_at: datetime | None = None
    
    @abstractmethod
    def _validate_payment_details(self) -> dict[str, bool | str]:
        """Validate payment-specific details (Template Method)."""
        pass
    
    @abstractmethod
    def _execute_payment(self) -> dict[str, bool | str]:
        """Execute the actual payment (Template Method)."""
        pass
    
    def process_payment(self) -> dict[str, bool | str]:
        """
        Process payment using Template Method Pattern.
        
        Interview Talking Point:
        "I use the Template Method pattern to define the payment flow.
        Subclasses only override the steps that differ, promoting code reuse."
        """
        # Step 1: Validate
        validation = self._validate_payment_details()
        if not validation["success"]:
            self.transaction.status = TransactionStatus.FAILED
            return validation
        
        # Step 2: Execute
        result = self._execute_payment()
        
        # Step 3: Update state
        if result["success"]:
            self.transaction.complete()
            self.processed_at = datetime.now()
        else:
            self.transaction.status = TransactionStatus.FAILED
        
        return result
    
    def get_receipt(self) -> str:
        """Generate payment receipt."""
        return f"""
{'=' * 50}
PAYMENT RECEIPT
{'=' * 50}
Transaction ID: {self.transaction.id}
Description: {self.transaction.description}
Amount: {self.transaction.amount}
Payment Method: {self.transaction.payment_method.value.upper()}
Status: {self.transaction.status.value.upper()}
Timestamp: {self.transaction.timestamp.isoformat()}
{'=' * 50}
"""


class UPIPayment(BasePayment):
    """UPI payment implementation (Concrete Strategy)."""
    
    def __init__(self, transaction: Transaction, upi_details: UPIDetails):
        super().__init__(transaction)
        self.upi_details = upi_details
    
    def _validate_payment_details(self) -> dict[str, bool | str]:
        """Validate UPI details (already validated in UPIDetails value object)."""
        return {"success": True, "message": "UPI details valid"}
    
    def _execute_payment(self) -> dict[str, bool | str]:
        """Execute UPI payment (mock implementation)."""
        # In production, this would call UPI gateway API
        return {
            "success": True,
            "message": f"UPI payment processed via {self.upi_details.app_name}",
            "upi_id": self.upi_details.upi_id,
            "transaction_id": f"UPI{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }


class CardPayment(BasePayment):
    """Card payment implementation (Concrete Strategy)."""
    
    def __init__(self, transaction: Transaction, card_details: CardDetails):
        super().__init__(transaction)
        self.card_details = card_details
    
    def _validate_payment_details(self) -> dict[str, bool | str]:
        """Validate card details (already validated in CardDetails value object)."""
        return {"success": True, "message": "Card details valid"}
    
    def _execute_payment(self) -> dict[str, bool | str]:
        """Execute card payment (mock implementation)."""
        # In production, this would call payment gateway API
        return {
            "success": True,
            "message": "Card payment processed",
            "card_type": self.card_details.card_type,
            "card_number": self.card_details.masked_number,
            "transaction_id": f"CARD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }


# ============================================================================
# FACTORY PATTERN (Creational Pattern)
# ============================================================================

class PaymentFactory:
    """
    Factory for creating payment objects (Factory Pattern).
    
    Architectural Why:
    - Centralizes object creation logic
    - Makes it easy to add new payment methods
    - Follows Open/Closed Principle
    
    Interview Talking Point:
    "I use the Factory pattern to encapsulate payment creation logic.
    Adding a new payment method only requires adding a new case here,
    without modifying existing code."
    """
    
    @staticmethod
    def create_payment(
        transaction: Transaction,
        payment_details: UPIDetails | CardDetails
    ) -> BasePayment:
        """
        Create appropriate payment object based on details type.
        
        Args:
            transaction: Transaction to process
            payment_details: Payment-specific details
        
        Returns:
            Concrete payment implementation
        
        Raises:
            ValueError: If payment details type is unsupported
        """
        if isinstance(payment_details, UPIDetails):
            return UPIPayment(transaction, payment_details)
        elif isinstance(payment_details, CardDetails):
            return CardPayment(transaction, payment_details)
        else:
            raise ValueError(f"Unsupported payment details type: {type(payment_details)}")


# ============================================================================
# DEMONSTRATION
# ============================================================================

def demonstrate_domain_models():
    """Demonstrate production-grade domain modeling."""
    print("=" * 70)
    print(" " * 15 + "NexTrack Domain Models - Production Grade")
    print("=" * 70)
    
    # Demo 1: Create transaction with Money value object
    print("\n[DEMO 1] Creating Transaction with Money Value Object")
    print("-" * 70)
    
    amount = Money(Decimal("150.50"), "USD")
    transaction = Transaction(
        description="Grocery shopping",
        amount=amount,
        category="Food",
        payment_method=PaymentMethod.UPI
    )
    print(f"Created: {transaction.description} - {transaction.amount}")
    print(f"Status: {transaction.status.value}")
    
    # Demo 2: Process UPI payment
    print("\n[DEMO 2] Processing UPI Payment")
    print("-" * 70)
    
    upi_details = UPIDetails(upi_id="user@paytm", app_name="Paytm")
    payment = PaymentFactory.create_payment(transaction, upi_details)
    result = payment.process_payment()
    
    print(f"Payment Result: {result}")
    print(f"Transaction Status: {transaction.status.value}")
    print(payment.get_receipt())
    
    # Demo 3: Card payment with validation
    print("\n[DEMO 3] Card Payment with Masked Number")
    print("-" * 70)
    
    card_transaction = Transaction(
        description="Online course",
        amount=Money(Decimal("500.00"), "USD"),
        category="Education",
        payment_method=PaymentMethod.CARD
    )
    
    card_details = CardDetails(
        card_number="1234567812345678",
        card_type="Visa",
        cvv="123"
    )
    
    card_payment = PaymentFactory.create_payment(card_transaction, card_details)
    card_result = card_payment.process_payment()
    
    print(f"Masked Card: {card_details.masked_number}")
    print(f"Payment Result: {card_result}")
    
    # Demo 4: Serialization
    print("\n[DEMO 4] Transaction Serialization (for JSON storage)")
    print("-" * 70)
    
    serialized = transaction.to_dict()
    print(f"Serialized: {serialized}")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] Domain model demonstration complete!")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_domain_models()
