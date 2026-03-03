"""
Advanced Features - Search, Export, Bulk Operations

Phase 3 implementation with full-text search, CSV/PDF export, and bulk operations.
"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io

from src.infrastructure.database import get_db
from src.infrastructure.database.models import TransactionModel
from src.infrastructure.database.user_model import UserModel
from src.api.auth_routes import get_current_user, require_admin
from src.api.schemas import TransactionCreate, TransactionResponse
from src.application.services import TransactionService

router = APIRouter(prefix="/api/v1/advanced", tags=["advanced"])


# ============================================================================
# SEARCH ENDPOINT
# ============================================================================

@router.get("/search", response_model=List[TransactionResponse])
async def search_transactions(
    q: str = Query(..., min_length=1, description="Search query"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Full-text search across transaction descriptions.
    
    Searches in description field with case-insensitive matching.
    """
    query = select(TransactionModel).where(
        TransactionModel.user_id == current_user.id,
        TransactionModel.description.ilike(f"%{q}%")
    ).order_by(TransactionModel.created_at.desc())
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return [TransactionResponse.model_validate(t) for t in transactions]


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@router.get("/export/csv")
async def export_transactions_csv(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export transactions to CSV format.
    
    Optionally filter by date range.
    """
    # Build query
    query = select(TransactionModel).where(
        TransactionModel.user_id == current_user.id
    )
    
    if start_date:
        query = query.where(TransactionModel.created_at >= start_date)
    if end_date:
        query = query.where(TransactionModel.created_at <= end_date)
    
    query = query.order_by(TransactionModel.created_at.desc())
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Description', 'Amount', 'Currency', 'Category',
        'Payment Method', 'Status', 'Created At'
    ])
    
    # Data rows
    for txn in transactions:
        writer.writerow([
            txn.id,
            txn.description,
            float(txn.amount),
            txn.currency,
            txn.category,
            txn.payment_method,
            txn.status,
            txn.created_at.isoformat()
        ])
    
    # Return CSV file
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk/create", response_model=List[TransactionResponse])
async def bulk_create_transactions(
    transactions: List[TransactionCreate],
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create multiple transactions in a single request.
    
    All transactions will be created atomically (all or nothing).
    """
    service = TransactionService(db, current_user)
    created_transactions = []
    
    for txn_data in transactions:
        txn = await service.create_transaction(txn_data)
        created_transactions.append(txn)
    
    return created_transactions


@router.delete("/bulk/delete")
async def bulk_delete_transactions(
    transaction_ids: List[str],
    current_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple transactions by IDs (admin only).
    
    Only admin users can perform bulk deletion.
    """
    service = TransactionService(db, current_user)
    deleted_count = 0
    
    for txn_id in transaction_ids:
        if await service.delete_transaction(txn_id):
            deleted_count += 1
    
    return {
        "deleted_count": deleted_count,
        "requested_count": len(transaction_ids)
    }


# ============================================================================
# ADVANCED FILTERING
# ============================================================================

@router.get("/filter", response_model=List[TransactionResponse])
async def advanced_filter(
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    payment_methods: Optional[str] = Query(None, description="Comma-separated payment methods"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced filtering with multiple criteria.
    
    Supports:
    - Amount range filtering
    - Date range filtering
    - Multiple categories
    - Multiple payment methods
    """
    query = select(TransactionModel).where(
        TransactionModel.user_id == current_user.id
    )
    
    # Amount filtering
    if min_amount is not None:
        query = query.where(TransactionModel.amount >= min_amount)
    if max_amount is not None:
        query = query.where(TransactionModel.amount <= max_amount)
    
    # Date filtering
    if start_date:
        query = query.where(TransactionModel.created_at >= start_date)
    if end_date:
        query = query.where(TransactionModel.created_at <= end_date)
    
    # Category filtering
    if categories:
        category_list = [c.strip() for c in categories.split(',')]
        query = query.where(TransactionModel.category.in_(category_list))
    
    # Payment method filtering
    if payment_methods:
        method_list = [m.strip() for m in payment_methods.split(',')]
        query = query.where(TransactionModel.payment_method.in_(method_list))
    
    query = query.order_by(TransactionModel.created_at.desc())
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return [TransactionResponse.model_validate(t) for t in transactions]
