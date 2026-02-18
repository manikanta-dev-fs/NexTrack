"""
Unit Tests for Domain Models

Tests for Transaction, Money, Payment classes and business logic.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from src.domain_models import (
    Transaction, Money, PaymentMethod, TransactionStatus,
    UPIDetails, CardDetails, UPIPayment, CardPayment, PaymentFactory
)


class TestMoney:
    """Test Money value object."""
    
    def test_money_creation(self):
        """Test creating Money object."""
        money = Money(Decimal("100.50"), "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"
    
    def test_money_validation_negative(self):
        """Test Money rejects negative amounts."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            Money(Decimal("-10"), "USD")
    
    def test_money_validation_zero(self):
        """Test Money rejects zero amounts."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            Money(Decimal("0"), "USD")
    
    def test_money_str_representation(self):
        """Test Money string representation."""
        money = Money(Decimal("100.50"), "USD")
        assert str(money) == "100.50 USD"


class TestTransaction:
    """Test Transaction aggregate root."""
    
    def test_transaction_creation(self):
        """Test creating valid transaction."""
        txn = Transaction(
            description="Test purchase",
            amount=Money(Decimal("50.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        assert txn.description == "Test purchase"
        assert txn.amount.amount == Decimal("50.00")
        assert txn.category == "Food"
        assert txn.payment_method == PaymentMethod.UPI
        assert txn.status == TransactionStatus.PENDING
        assert txn.id is not None
        assert isinstance(txn.timestamp, datetime)
    
    def test_transaction_validation_empty_description(self):
        """Test transaction rejects empty description."""
        with pytest.raises(ValueError, match="Description cannot be empty"):
            Transaction(
                description="",
                amount=Money(Decimal("50.00"), "USD"),
                category="Food",
                payment_method=PaymentMethod.UPI
            )
    
    def test_transaction_validation_invalid_category(self):
        """Test transaction rejects invalid category."""
        with pytest.raises(ValueError, match="Invalid category"):
            Transaction(
                description="Test",
                amount=Money(Decimal("50.00"), "USD"),
                category="InvalidCategory",
                payment_method=PaymentMethod.UPI
            )
    
    def test_transaction_mark_completed(self):
        """Test marking transaction as completed."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("50.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        txn.mark_completed()
        assert txn.status == TransactionStatus.COMPLETED
    
    def test_transaction_mark_failed(self):
        """Test marking transaction as failed."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("50.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        txn.mark_failed()
        assert txn.status == TransactionStatus.FAILED


class TestUPIPayment:
    """Test UPI payment processing."""
    
    def test_upi_payment_success(self):
        """Test successful UPI payment."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("100.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        upi_details = UPIDetails(upi_id="test@paytm", app_name="Paytm")
        payment = UPIPayment(txn, upi_details)
        
        result = payment.process_payment()
        
        assert result["success"] is True
        assert "transaction_id" in result
        assert txn.status == TransactionStatus.COMPLETED
    
    def test_upi_payment_invalid_id(self):
        """Test UPI payment with invalid ID."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("100.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        upi_details = UPIDetails(upi_id="invalid", app_name="Paytm")
        payment = UPIPayment(txn, upi_details)
        
        result = payment.process_payment()
        
        assert result["success"] is False
        assert "error" in result
        assert txn.status == TransactionStatus.FAILED


class TestCardPayment:
    """Test card payment processing."""
    
    def test_card_payment_success(self):
        """Test successful card payment."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("200.00"), "USD"),
            category="Shopping",
            payment_method=PaymentMethod.CARD
        )
        
        card_details = CardDetails(
            card_number="1234567812345678",
            card_type="Visa",
            cvv="123"
        )
        payment = CardPayment(txn, card_details)
        
        result = payment.process_payment()
        
        assert result["success"] is True
        assert "authorization_code" in result
        assert txn.status == TransactionStatus.COMPLETED
    
    def test_card_payment_invalid_cvv(self):
        """Test card payment with invalid CVV."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("200.00"), "USD"),
            category="Shopping",
            payment_method=PaymentMethod.CARD
        )
        
        card_details = CardDetails(
            card_number="1234567812345678",
            card_type="Visa",
            cvv="12"  # Invalid: too short
        )
        payment = CardPayment(txn, card_details)
        
        result = payment.process_payment()
        
        assert result["success"] is False
        assert txn.status == TransactionStatus.FAILED


class TestPaymentFactory:
    """Test Payment Factory pattern."""
    
    def test_factory_creates_upi_payment(self):
        """Test factory creates UPI payment."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("100.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        upi_details = UPIDetails(upi_id="test@paytm", app_name="Paytm")
        payment = PaymentFactory.create_payment(txn, upi_details)
        
        assert isinstance(payment, UPIPayment)
    
    def test_factory_creates_card_payment(self):
        """Test factory creates card payment."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("200.00"), "USD"),
            category="Shopping",
            payment_method=PaymentMethod.CARD
        )
        
        card_details = CardDetails(
            card_number="1234567812345678",
            card_type="Visa",
            cvv="123"
        )
        payment = PaymentFactory.create_payment(txn, card_details)
        
        assert isinstance(payment, CardPayment)
    
    def test_factory_rejects_invalid_details(self):
        """Test factory rejects mismatched payment details."""
        txn = Transaction(
            description="Test",
            amount=Money(Decimal("100.00"), "USD"),
            category="Food",
            payment_method=PaymentMethod.UPI
        )
        
        # Trying to use card details for UPI payment
        card_details = CardDetails(
            card_number="1234567812345678",
            card_type="Visa",
            cvv="123"
        )
        
        with pytest.raises(ValueError):
            PaymentFactory.create_payment(txn, card_details)
