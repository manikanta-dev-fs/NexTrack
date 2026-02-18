"""
API Integration Tests

Tests for all FastAPI endpoints with success and error cases.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.infrastructure.database.config import init_db, drop_db


@pytest.fixture(scope="function")
async def client():
    """Create test client with fresh database."""
    # Initialize database
    await init_db()
    
    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Cleanup
    await drop_db()


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    async def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "NexTrack API"
        assert data["version"] == "2.0.0"


@pytest.mark.asyncio
class TestTransactionEndpoints:
    """Test transaction CRUD endpoints."""
    
    async def test_create_transaction_upi(self, client):
        """Test creating transaction with UPI payment."""
        payload = {
            "description": "Test grocery shopping",
            "amount": 150.50,
            "currency": "USD",
            "category": "Food",
            "payment_method": "upi",
            "payment_details": {
                "upi_id": "test@paytm",
                "app_name": "Paytm"
            }
        }
        
        response = await client.post("/api/v1/transactions", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test grocery shopping"
        assert float(data["amount"]) == 150.50
        assert data["category"] == "Food"
        assert data["payment_method"] == "upi"
        assert "id" in data
        assert data["status"] == "completed"
    
    async def test_create_transaction_card(self, client):
        """Test creating transaction with card payment."""
        payload = {
            "description": "Online course",
            "amount": 500.00,
            "currency": "USD",
            "category": "Education",
            "payment_method": "card",
            "payment_details": {
                "card_number": "1234567812345678",
                "card_type": "Visa",
                "cvv": "123"
            }
        }
        
        response = await client.post("/api/v1/transactions", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Online course"
        assert data["category"] == "Education"
        assert data["payment_method"] == "card"
    
    async def test_create_transaction_validation_error(self, client):
        """Test transaction creation with invalid data."""
        payload = {
            "description": "",  # Invalid: empty
            "amount": -50,  # Invalid: negative
            "category": "Food",
            "payment_method": "upi"
        }
        
        response = await client.post("/api/v1/transactions", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    async def test_list_transactions(self, client):
        """Test listing transactions with pagination."""
        # Create some transactions first
        for i in range(5):
            payload = {
                "description": f"Transaction {i}",
                "amount": 100.00 + i,
                "currency": "USD",
                "category": "Food",
                "payment_method": "upi",
                "payment_details": {
                    "upi_id": "test@paytm",
                    "app_name": "Paytm"
                }
            }
            await client.post("/api/v1/transactions", json=payload)
        
        # List transactions
        response = await client.get("/api/v1/transactions?page=1&page_size=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert len(data["transactions"]) == 3
    
    async def test_list_transactions_filter_by_category(self, client):
        """Test filtering transactions by category."""
        # Create transactions in different categories
        categories = ["Food", "Travel", "Food"]
        for i, category in enumerate(categories):
            payload = {
                "description": f"Transaction {i}",
                "amount": 100.00,
                "currency": "USD",
                "category": category,
                "payment_method": "upi",
                "payment_details": {
                    "upi_id": "test@paytm",
                    "app_name": "Paytm"
                }
            }
            await client.post("/api/v1/transactions", json=payload)
        
        # Filter by Food category
        response = await client.get("/api/v1/transactions?category=Food")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(t["category"] == "Food" for t in data["transactions"])
    
    async def test_get_transaction_by_id(self, client):
        """Test getting specific transaction."""
        # Create transaction
        payload = {
            "description": "Test transaction",
            "amount": 75.00,
            "currency": "USD",
            "category": "Shopping",
            "payment_method": "upi",
            "payment_details": {
                "upi_id": "test@paytm",
                "app_name": "Paytm"
            }
        }
        create_response = await client.post("/api/v1/transactions", json=payload)
        transaction_id = create_response.json()["id"]
        
        # Get transaction
        response = await client.get(f"/api/v1/transactions/{transaction_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transaction_id
        assert data["description"] == "Test transaction"
    
    async def test_get_transaction_not_found(self, client):
        """Test getting non-existent transaction."""
        response = await client.get("/api/v1/transactions/nonexistent-id")
        
        assert response.status_code == 404
    
    async def test_update_transaction(self, client):
        """Test updating transaction."""
        # Create transaction
        payload = {
            "description": "Original description",
            "amount": 100.00,
            "currency": "USD",
            "category": "Food",
            "payment_method": "upi",
            "payment_details": {
                "upi_id": "test@paytm",
                "app_name": "Paytm"
            }
        }
        create_response = await client.post("/api/v1/transactions", json=payload)
        transaction_id = create_response.json()["id"]
        
        # Update transaction
        update_payload = {
            "description": "Updated description",
            "category": "Shopping"
        }
        response = await client.patch(
            f"/api/v1/transactions/{transaction_id}",
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["category"] == "Shopping"
    
    async def test_delete_transaction(self, client):
        """Test deleting transaction."""
        # Create transaction
        payload = {
            "description": "To be deleted",
            "amount": 50.00,
            "currency": "USD",
            "category": "Food",
            "payment_method": "upi",
            "payment_details": {
                "upi_id": "test@paytm",
                "app_name": "Paytm"
            }
        }
        create_response = await client.post("/api/v1/transactions", json=payload)
        transaction_id = create_response.json()["id"]
        
        # Delete transaction
        response = await client.delete(f"/api/v1/transactions/{transaction_id}")
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(f"/api/v1/transactions/{transaction_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestStatisticsEndpoint:
    """Test statistics endpoint."""
    
    async def test_get_statistics(self, client):
        """Test getting transaction statistics."""
        # Create transactions
        transactions = [
            {"category": "Food", "amount": 100.00},
            {"category": "Food", "amount": 150.00},
            {"category": "Travel", "amount": 200.00},
        ]
        
        for txn in transactions:
            payload = {
                "description": "Test",
                "amount": txn["amount"],
                "currency": "USD",
                "category": txn["category"],
                "payment_method": "upi",
                "payment_details": {
                    "upi_id": "test@paytm",
                    "app_name": "Paytm"
                }
            }
            await client.post("/api/v1/transactions", json=payload)
        
        # Get statistics
        response = await client.get("/api/v1/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 3
        assert float(data["total_amount"]) == 450.00
        assert "Food" in data["by_category"]
        assert "Travel" in data["by_category"]
        assert data["by_category"]["Food"]["count"] == 2
        assert data["by_category"]["Travel"]["count"] == 1
