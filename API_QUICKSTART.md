# NexTrack Production API - Quick Start Guide

## 🚀 Getting Started

### Option 1: Docker (Recommended)

```powershell
# Start PostgreSQL and API
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

Access API at: http://localhost:8000/docs

---

### Option 2: Local Development

#### Step 1: Install Dependencies

```powershell
pip install -r requirements.txt
```

#### Step 2: Setup PostgreSQL

**Option A: Docker PostgreSQL Only**
```powershell
docker-compose up -d postgres
```

**Option B: Local PostgreSQL**
```powershell
# Install PostgreSQL, then:
createdb nextrack_db
```

#### Step 3: Run Migrations

```powershell
# Create tables
alembic upgrade head
```

#### Step 4: Start API Server

```powershell
# Development mode (auto-reload)
uvicorn src.api.main:app --reload

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

---

## 📚 API Documentation

### Interactive Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health Check
```powershell
curl http://localhost:8000/health
```

---

## 🧪 Testing the API

### Create Transaction (UPI)

```powershell
curl -X POST "http://localhost:8000/api/v1/transactions" `
  -H "Content-Type: application/json" `
  -d '{
    "description": "Grocery shopping",
    "amount": 150.50,
    "currency": "USD",
    "category": "Food",
    "payment_method": "upi",
    "payment_details": {
      "upi_id": "user@paytm",
      "app_name": "Paytm"
    }
  }'
```

### Create Transaction (Card)

```powershell
curl -X POST "http://localhost:8000/api/v1/transactions" `
  -H "Content-Type: application/json" `
  -d '{
    "description": "Python course",
    "amount": 500.00,
    "currency": "USD",
    "category": "Education",
    "payment_method": "card",
    "payment_details": {
      "card_number": "1234567812345678",
      "card_type": "Visa",
      "cvv": "123"
    }
  }'
```

### List Transactions

```powershell
# All transactions
curl http://localhost:8000/api/v1/transactions

# With pagination
curl "http://localhost:8000/api/v1/transactions?page=1&page_size=10"

# Filter by category
curl "http://localhost:8000/api/v1/transactions?category=Food"
```

### Get Statistics

```powershell
curl http://localhost:8000/api/v1/statistics
```

---

## 🗄️ Database Management

### View Database

```powershell
# Connect to PostgreSQL
docker exec -it nextrack_postgres psql -U postgres -d nextrack_db

# List tables
\dt

# View transactions
SELECT * FROM transactions;

# Exit
\q
```

### Reset Database

```powershell
# Downgrade all migrations
alembic downgrade base

# Re-run migrations
alembic upgrade head
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│     FastAPI (Presentation)          │
│  - REST endpoints                   │
│  - Pydantic validation              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Application Service Layer          │
│  - Use case orchestration           │
│  - Domain logic integration         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Domain Layer                    │
│  - Business logic                   │
│  - Payment processing               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Infrastructure (PostgreSQL)        │
│  - SQLAlchemy ORM                   │
│  - Database persistence             │
└─────────────────────────────────────┘
```

---

## 🎯 Key Features

✅ **RESTful API** with FastAPI
✅ **PostgreSQL** for production-grade persistence
✅ **Async I/O** for high performance
✅ **Pydantic** validation for type safety
✅ **SQLAlchemy** ORM with relationships
✅ **Alembic** migrations for schema versioning
✅ **Docker** for easy deployment
✅ **OpenAPI** auto-generated documentation
✅ **CORS** enabled for frontend integration
✅ **Health checks** for monitoring

---

## 📊 Database Schema

### Transactions Table
- `id` (UUID) - Primary key
- `description` (VARCHAR) - Transaction description
- `amount` (DECIMAL) - Transaction amount
- `currency` (VARCHAR) - Currency code
- `category` (VARCHAR) - Category
- `payment_method` (VARCHAR) - Payment method
- `status` (VARCHAR) - Transaction status
- `metadata` (JSONB) - Flexible metadata
- `created_at` (TIMESTAMP) - Creation time
- `updated_at` (TIMESTAMP) - Last update time

### Payment Details Table
- `id` (UUID) - Primary key
- `transaction_id` (UUID) - Foreign key to transactions
- `payment_type` (VARCHAR) - Payment type
- `details` (JSONB) - Payment details
- `processed_at` (TIMESTAMP) - Processing time
- `created_at` (TIMESTAMP) - Creation time

---

## 🔧 Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/nextrack_db

# API configuration
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 🎓 Interview Talking Points

**Q: "Why FastAPI over Flask?"**
**A:** "FastAPI is async-native, has built-in Pydantic validation, auto-generates OpenAPI docs, and is one of the fastest Python frameworks. Perfect for modern, high-performance APIs."

**Q: "How do you handle database migrations?"**
**A:** "I use Alembic for version-controlled schema migrations. This allows safe, reversible database changes in production without data loss."

**Q: "What's your deployment strategy?"**
**A:** "I use Docker for containerization. In production, I'd deploy to Kubernetes with separate database and API pods, using managed PostgreSQL like AWS RDS or Google Cloud SQL."

---

## 🚀 Production Checklist

- [ ] Set strong database password
- [ ] Configure CORS for specific origins
- [ ] Add authentication (JWT tokens)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure logging (structured JSON logs)
- [ ] Add rate limiting
- [ ] Set up CI/CD pipeline
- [ ] Configure SSL/TLS
- [ ] Add backup strategy
- [ ] Set up error tracking (Sentry)

---

**Your NexTrack API is now production-ready!** 🎉
