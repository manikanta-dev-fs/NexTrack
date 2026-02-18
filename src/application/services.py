"""
Application Service Layer - With User Authentication

Production-grade service layer with user-specific data isolation.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from decimal import Decimal
from datetime import datetime
from typing import Optional

from src.infrastructure.database.models import TransactionModel, PaymentDetailModel
from src.infrastructure.database.user_model import UserModel
from src.api.schemas import (
    TransactionCreate, TransactionResponse, TransactionListResponse,
    StatisticsResponse, CategoryStats, TransactionUpdate
)
from src.domain_models import (
    Transaction, Money, PaymentMethod, TransactionStatus,
    UPIDetails, CardDetails, PaymentFactory
)


class TransactionService:
    """
    Application service for transaction operations with user authentication.
    """
    
    def __init__(self, db: AsyncSession, user: Optional[UserModel] = None):
        self.db = db
        self.user = user
    
    async def create_transaction(self, data: TransactionCreate) -> TransactionResponse:
        """Create and process a new transaction for authenticated user."""
        if not self.user:
            raise ValueError("User authentication required")
        
        # Convert Pydantic to domain objects
        payment_method = PaymentMethod(data.payment_method.upper())
        
        # Create domain transaction
        transaction = Transaction(
            description=data.description,
            amount=Money(data.amount, data.currency),
            category=data.category,
            payment_method=payment_method
        )
        
        # Convert payment details to domain objects
        if data.payment_method == "upi":
            payment_details = UPIDetails(
                upi_id=data.payment_details.upi_id,
                app_name=data.payment_details.app_name
            )
        elif data.payment_method == "card":
            payment_details = CardDetails(
                card_number=data.payment_details.card_number,
                card_type=data.payment_details.card_type,
                cvv=data.payment_details.cvv
            )
        else:
            raise ValueError(f"Unsupported payment method: {data.payment_method}")
        
        # Process payment using domain logic
        payment = PaymentFactory.create_payment(transaction, payment_details)
        payment_result = payment.process_payment()
        
        if not payment_result["success"]:
            raise ValueError(payment_result.get("error", "Payment processing failed"))
        
        # Persist to database with user ownership
        db_transaction = TransactionModel(
            id=transaction.id,
            user_id=self.user.id,  # Associate with user
            description=transaction.description,
            amount=float(transaction.amount.amount),
            currency=transaction.amount.currency,
            category=transaction.category,
            payment_method=transaction.payment_method.value.lower(),
            status=transaction.status.value,
            created_at=transaction.timestamp,
            updated_at=transaction.timestamp
        )
        
        db_payment = PaymentDetailModel(
            transaction_id=transaction.id,
            payment_type=data.payment_method,
            details=payment_result,
            processed_at=payment.processed_at
        )
        
        self.db.add(db_transaction)
        self.db.add(db_payment)
        await self.db.flush()
        await self.db.refresh(db_transaction)
        
        return TransactionResponse.model_validate(db_transaction)
    
    async def get_transactions(
        self,
        page: int = 1,
        page_size: int = 10,
        category: str | None = None,
        status: str | None = None
    ) -> TransactionListResponse:
        """Get paginated list of user's transactions."""
        if not self.user:
            raise ValueError("User authentication required")
        
        # Build query filtered by user
        query = select(TransactionModel).where(
            TransactionModel.user_id == self.user.id
        ).options(selectinload(TransactionModel.payment_details))
        
        if category:
            query = query.where(TransactionModel.category == category)
        if status:
            query = query.where(TransactionModel.status == status)
        
        query = query.order_by(TransactionModel.created_at.desc())
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.db.execute(query)
        transactions = result.scalars().all()
        
        return TransactionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            transactions=[TransactionResponse.model_validate(t) for t in transactions]
        )
    
    async def get_transaction_by_id(self, transaction_id: str) -> TransactionResponse | None:
        """Get a specific transaction (user-owned only)."""
        if not self.user:
            raise ValueError("User authentication required")
        
        query = select(TransactionModel).where(
            TransactionModel.id == transaction_id,
            TransactionModel.user_id == self.user.id  # User ownership check
        ).options(selectinload(TransactionModel.payment_details))
        
        result = await self.db.execute(query)
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return None
        
        return TransactionResponse.model_validate(transaction)
    
    async def update_transaction(
        self,
        transaction_id: str,
        data: TransactionUpdate
    ) -> TransactionResponse | None:
        """Update a transaction (user-owned only)."""
        if not self.user:
            raise ValueError("User authentication required")
        
        query = select(TransactionModel).where(
            TransactionModel.id == transaction_id,
            TransactionModel.user_id == self.user.id  # User ownership check
        )
        result = await self.db.execute(query)
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return None
        
        if data.description is not None:
            transaction.description = data.description
        if data.category is not None:
            transaction.category = data.category
        if data.status is not None:
            transaction.status = data.status
        
        transaction.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(transaction)
        
        return TransactionResponse.model_validate(transaction)
    
    async def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction (user-owned only)."""
        if not self.user:
            raise ValueError("User authentication required")
        
        query = delete(TransactionModel).where(
            TransactionModel.id == transaction_id,
            TransactionModel.user_id == self.user.id  # User ownership check
        )
        result = await self.db.execute(query)
        return result.rowcount > 0
    
    async def get_statistics(self) -> StatisticsResponse:
        """Get comprehensive transaction statistics for user."""
        if not self.user:
            raise ValueError("User authentication required")
        
        # Total count and amount (user-specific)
        total_query = select(
            func.count(TransactionModel.id).label("count"),
            func.sum(TransactionModel.amount).label("total")
        ).where(TransactionModel.user_id == self.user.id)
        
        total_result = await self.db.execute(total_query)
        total_row = total_result.one()
        total_count = total_row.count or 0
        total_amount = Decimal(str(total_row.total or 0))
        
        # By category (user-specific)
        category_query = select(
            TransactionModel.category,
            func.count(TransactionModel.id).label("count"),
            func.sum(TransactionModel.amount).label("total"),
            func.avg(TransactionModel.amount).label("average")
        ).where(
            TransactionModel.user_id == self.user.id
        ).group_by(TransactionModel.category)
        
        category_result = await self.db.execute(category_query)
        by_category = {
            row.category: CategoryStats(
                count=row.count,
                total=Decimal(str(row.total)),
                average=Decimal(str(row.average))
            )
            for row in category_result
        }
        
        # By payment method (user-specific)
        payment_query = select(
            TransactionModel.payment_method,
            func.count(TransactionModel.id).label("count")
        ).where(
            TransactionModel.user_id == self.user.id
        ).group_by(TransactionModel.payment_method)
        
        payment_result = await self.db.execute(payment_query)
        by_payment_method = {row.payment_method: row.count for row in payment_result}
        
        return StatisticsResponse(
            total_transactions=total_count,
            total_amount=total_amount,
            by_category=by_category,
            by_payment_method=by_payment_method
        )
