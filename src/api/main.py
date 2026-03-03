"""
FastAPI Application - Production REST API with Authentication & RBAC

Enterprise-grade API with JWT authentication, role-based access control,
structured error handling, and comprehensive monitoring.
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from jose import ExpiredSignatureError, JWTError
import uvicorn
import os

from src.infrastructure.database import get_db, init_db
from src.api.schemas import (
    TransactionCreate, TransactionResponse, TransactionListResponse,
    StatisticsResponse, HealthResponse, ErrorResponse, TransactionUpdate
)
from src.api.auth_routes import router as auth_router, get_current_user, require_admin
from src.api.auth_schemas import UserResponse
from src.api.advanced_routes import router as advanced_router
from src.infrastructure.database.user_model import UserModel
from src.application.services import TransactionService
from src.infrastructure.monitoring import (
    PerformanceMonitoringMiddleware,
    ErrorTrackingMiddleware,
    metrics,
    logger
)


# Create FastAPI application
app = FastAPI(
    title="NexTrack API",
    description="""
    **Production-Grade Expense Tracking System with Authentication & RBAC**
    
    Built with:
    - FastAPI for high-performance async API
    - SQLite for reliable data persistence
    - SQLAlchemy for type-safe ORM
    - Pydantic for request/response validation
    - JWT authentication with role-based access control
    - Domain-Driven Design patterns
    
    Features:
    - User registration and authentication
    - Role-based access control (admin / user)
    - Transaction management with multiple payment methods
    - Real-time statistics and analytics
    - Pagination and filtering
    - User-specific data isolation
    - Structured error responses
    - Performance monitoring with request tracing
    - Automatic OpenAPI documentation
    """,
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "authentication", "description": "User registration, login, and profile"},
        {"name": "health", "description": "Health check endpoints"},
        {"name": "transactions", "description": "Transaction management"},
        {"name": "statistics", "description": "Analytics and reporting"},
        {"name": "advanced", "description": "Advanced features: search, export, bulk operations"},
        {"name": "admin", "description": "Admin-only endpoints (requires admin role)"},
        {"name": "monitoring", "description": "Metrics and monitoring"},
    ]
)

# Add monitoring middleware
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(ErrorTrackingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(advanced_router)


# ============================================================================
# STRUCTURED ERROR HANDLERS
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "message": str(exc)}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
        headers=getattr(exc, "headers", None)
    )


@app.exception_handler(ExpiredSignatureError)
async def expired_token_handler(request, exc):
    """Handle expired JWT tokens."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "message": "Token has expired"},
        headers={"WWW-Authenticate": "Bearer"}
    )


@app.exception_handler(JWTError)
async def jwt_error_handler(request, exc):
    """Handle all JWT errors (invalid claims, malformed tokens, etc)."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "message": "Invalid or malformed token"},
        headers={"WWW-Authenticate": "Bearer"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unhandled error: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Internal server error"}
    )


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting NexTrack API v2.1.0...")
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down NexTrack API...")


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check"
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    try:
        await db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        service="NexTrack API",
        version="2.1.0",
        database=db_status
    )


# ============================================================================
# TRANSACTION ENDPOINTS (Protected)
# ============================================================================

@app.post(
    "/api/v1/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["transactions"],
    summary="Create transaction"
)
async def create_transaction(
    transaction: TransactionCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new transaction (requires authentication).
    
    The transaction will be associated with the authenticated user.
    """
    service = TransactionService(db, current_user)
    return await service.create_transaction(transaction)


@app.get(
    "/api/v1/transactions",
    response_model=TransactionListResponse,
    tags=["transactions"],
    summary="List transactions"
)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of user's transactions (requires authentication).
    
    Only returns transactions belonging to the authenticated user.
    """
    service = TransactionService(db, current_user)
    return await service.get_transactions(page, page_size, category, status)


@app.get(
    "/api/v1/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["transactions"],
    summary="Get transaction"
)
async def get_transaction(
    transaction_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific transaction (requires authentication)."""
    service = TransactionService(db, current_user)
    transaction = await service.get_transaction_by_id(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@app.patch(
    "/api/v1/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["transactions"],
    summary="Update transaction"
)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update transaction (requires authentication)."""
    service = TransactionService(db, current_user)
    transaction = await service.update_transaction(transaction_id, data)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@app.delete(
    "/api/v1/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["transactions"],
    summary="Delete transaction"
)
async def delete_transaction(
    transaction_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a transaction (requires authentication)."""
    service = TransactionService(db, current_user)
    deleted = await service.delete_transaction(transaction_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return None


# ============================================================================
# STATISTICS ENDPOINTS (Protected)
# ============================================================================

@app.get(
    "/api/v1/statistics",
    response_model=StatisticsResponse,
    tags=["statistics"],
    summary="Get statistics"
)
async def get_statistics(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction statistics for authenticated user.
    
    Returns user-specific statistics only.
    """
    service = TransactionService(db, current_user)
    return await service.get_statistics()


# ============================================================================
# ADMIN ENDPOINTS (Admin Only)
# ============================================================================

@app.get(
    "/admin/users",
    response_model=List[UserResponse],
    tags=["admin"],
    summary="List all users (admin only)"
)
async def list_all_users(
    current_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all registered users (admin only).
    
    Returns all user accounts. Requires admin role.
    """
    query = select(UserModel).order_by(UserModel.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@app.get(
    "/admin/metrics",
    tags=["admin"],
    summary="Get API metrics (admin only)"
)
async def get_api_metrics(
    current_user: UserModel = Depends(require_admin),
):
    """
    Get API performance metrics (admin only).
    
    Returns request counts, error rates, and per-endpoint breakdowns.
    """
    return {"success": True, "data": metrics.get_metrics()}


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
