# Trading Platform API 📈

A production-ready mini stock trading backend system built with **FastAPI**, **MySQL**, and **Redis**. Designed to handle real-time price updates, order execution, wallet management, and portfolio tracking efficiently.

## 🎯 Features

### Core Features
- ✅ **User Management** - Create users with auto-generated wallet (₹10,00,000)
- ✅ **Wallet System** - Track user balances with real-time updates
- ✅ **Market Prices** - Real-time price storage in Redis (updated every 1 second)
- ✅ **Order Execution** - BUY/SELL orders with instant execution
- ✅ **Position Management** - Track holdings with weighted average price
- ✅ **Portfolio Analytics** - Real-time P&L calculations and portfolio value
- ✅ **Order History** - Complete order tracking and history
- ✅ **WebSocket** - Real-time order and price updates

### Technical Features
- 🔄 Async/await throughout (FastAPI native)
- 🛡️ SQLAlchemy ORM (type-safe database operations)
- 💾 Redis integration (real-time data)
- 📡 WebSocket for live updates
- 🔐 Proper error handling and validation
- 📚 Auto-generated Swagger API documentation
- 🎨 Clean, modular architecture
- 🧪 Production-ready code

## 📋 Project Structure

```
project/
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, background tasks, WebSocket
│   ├── database.py             # SQLAlchemy setup and session management
│   ├── config.py               # Environment configuration
│   │
│   ├── models/
│   │   └── __init__.py         # User, Wallet, Order, Position models
│   │
│   ├── schemas/
│   │   └── __init__.py         # Pydantic validation schemas
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py            # User management endpoints
│   │   ├── orders.py           # Order execution endpoints
│   │   ├── portfolio.py        # Portfolio analytics endpoints
│   │   └── market.py           # Market data endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py     # User business logic
│   │   ├── wallet_service.py   # Wallet operations
│   │   ├── order_service.py    # Order execution logic
│   │   ├── position_service.py # Position management
│   │   └── price_service.py    # Market price management
│   │
│   ├── websocket/
│   │   ├── __init__.py
│   │   └── manager.py          # WebSocket connection management
│   │
│   └── utils/
│       ├── __init__.py
│       └── redis_manager.py    # Redis operations
│
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- Redis 6.0+
- pip or Poetry

### 1. Clone and Setup

```bash
# Navigate to project directory
cd TradingSys

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create or update `.env` file with your database and Redis credentials:

```env
# Database Configuration
DB_URL=mysql+pymysql://root:password@localhost/trading_db
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=trading_db

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# App Configuration
APP_NAME=Trading Platform API
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
```

### 4. Create MySQL Database

```bash
mysql -u root -p

# In MySQL shell:
CREATE DATABASE trading_db;
CREATE USER 'trading_user'@'localhost' IDENTIFIED BY 'trading_password';
GRANT ALL PRIVILEGES ON trading_db.* TO 'trading_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Start Redis

```bash
# On Linux/Mac:
redis-server

# On Windows (if installed):
redis-server.exe

# Using Docker:
docker run -d -p 6379:6379 redis:latest
```

### 6. Start FastAPI Server

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: **http://localhost:8000**

### 7. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📚 API Documentation

### 0. System Health & Monitoring

#### Check Overall System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-15T10:30:00",
  "uptime": {
    "seconds": 3600,
    "formatted": "1h"
  },
  "components": {
    "database": {"status": "healthy", "connected": true},
    "redis": {"status": "healthy", "connected": true}
  },
  "metrics": {
    "cpu_percent": 15.2,
    "memory": {"percent": 50.0, "used_mb": 4096}
  }
}
```

#### Quick Health Check (for load balancers)
```http
GET /health/quick
```

**Response:**
```json
{
  "status": "ok|warning|error",
  "database": "✅|❌",
  "redis": "✅|❌",
  "uptime_seconds": 3600
}
```

#### Check Redis Connection
```http
GET /health/redis
```

#### Check Database Connection
```http
GET /health/database
```

#### Get Server Metrics
```http
GET /health/metrics
```

#### Force Redis Reconnection
```http
POST /redis/reconnect
```

**For complete health check documentation, see:** [HEALTH_CHECK_API.md](./HEALTH_CHECK_API.md) and [HEALTH_CHECK_QUICK_REF.md](./HEALTH_CHECK_QUICK_REF.md)

---

### 1. User Management

#### Create User
```http
POST /users
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

#### Get User
```http
GET /users/{user_id}
```

#### Get All Users
```http
GET /users?skip=0&limit=100
```

#### Delete User
```http
DELETE /users/{user_id}
```

---

### 2. Market Prices

#### Get All Prices
```http
GET /market/prices
```

**Response:**
```json
{
  "SBIN": 2450.50,
  "RELIANCE": 3200.75,
  "TCS": 3600.00,
  "INFY": 1850.25,
  "HDFC": 2750.00
}
```

#### Get Single Symbol Price
```http
GET /market/price/{symbol}
```

---

### 3. Order Execution

#### Create Order (BUY)
```http
POST /orders
Content-Type: application/json

{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 10,
  "side": "BUY"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "symbol": "SBIN",
  "quantity": 10,
  "price": 2450.50,
  "total_amount": 24505.00,
  "side": "BUY",
  "status": "COMPLETED",
  "created_at": "2024-01-15T10:35:00",
  "updated_at": "2024-01-15T10:35:00"
}
```

#### Create Order (SELL)
```http
POST /orders
Content-Type: application/json

{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 5,
  "side": "SELL"
}
```

#### Get Order History
```http
GET /orders/{user_id}?skip=0&limit=50
```

---

### 4. Portfolio Management

#### Get Complete Portfolio
```http
GET /portfolio/{user_id}
```

**Response:**
```json
{
  "user_id": 1,
  "wallet_balance": 975495.00,
  "holdings": [
    {
      "symbol": "SBIN",
      "quantity": 10,
      "average_price": 2450.50,
      "current_price": 2480.75,
      "total_invested": 24505.00,
      "current_value": 24807.50,
      "unrealized_pnl": 302.50,
      "pnl_percentage": 1.23
    }
  ],
  "total_portfolio_value": 1000302.50,
  "total_invested": 24505.00,
  "total_unrealized_pnl": 302.50,
  "total_pnl_percentage": 1.23
}
```

#### Get Wallet Balance
```http
GET /portfolio/{user_id}/balance
```

#### Get Open Positions
```http
GET /portfolio/{user_id}/positions
```

---

### 5. WebSocket (Real-Time Updates)

#### Connect to WebSocket
```javascript
// JavaScript example
const ws = new WebSocket('ws://localhost:8000/ws/1');

ws.onopen = () => {
  console.log('Connected to trading updates');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Update:', message);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

#### Message Types

**Order Executed:**
```json
{
  "event": "order_executed",
  "symbol": "SBIN",
  "qty": 10,
  "price": 2450.50,
  "side": "BUY",
  "status": "COMPLETED",
  "total_amount": 24505.00,
  "timestamp": "2024-01-15T10:35:00"
}
```

**Price Update:**
```json
{
  "event": "price_update",
  "symbol": "SBIN",
  "price": 2480.75,
  "timestamp": "2024-01-15T10:36:00"
}
```

---

## 🔄 Order Processing Flow

### BUY Order
1. User sends POST /orders with BUY side
2. System fetches current price from Redis
3. Validates wallet has sufficient balance
4. Deducts amount from wallet
5. Updates position (creates new or updates with weighted avg price)
6. Creates order record with status = COMPLETED
7. Broadcasts order execution via WebSocket
8. Returns order details

### SELL Order
1. User sends POST /orders with SELL side
2. System fetches current price from Redis
3. Validates user has sufficient quantity
4. Reduces position quantity
5. Adds proceeds to wallet
6. Creates order record with status = COMPLETED
7. Broadcasts order execution via WebSocket
8. Returns order details

---

## 💡 Example Workflow

### 1. Create a User
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Johnson","email":"alice@example.com"}'
```

### 2. Check Wallet Balance
```bash
curl http://localhost:8000/portfolio/1/balance
```

### 3. Get Current Prices
```bash
curl http://localhost:8000/market/prices
```

### 4. Place BUY Order
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "symbol": "SBIN",
    "qty": 5,
    "side": "BUY"
  }'
```

### 5. View Portfolio
```bash
curl http://localhost:8000/portfolio/1
```

### 6. Connect WebSocket
```bash
# Using wscat
wscat -c ws://localhost:8000/ws/1
```

---

## 🛡️ Error Handling

The API returns proper HTTP status codes and error messages:

### 400 Bad Request
- Insufficient balance
- Insufficient quantity
- Invalid order side
- Missing required fields

### 404 Not Found
- User not found
- Symbol price not found
- Order not found

### 500 Internal Server Error
- Database connection failure
- Redis connection failure
- Unexpected server error

**Error Response Format:**
```json
{
  "detail": "Insufficient balance for this order"
}
```

---

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Wallets Table
```sql
CREATE TABLE wallets (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT UNIQUE NOT NULL,
  balance FLOAT DEFAULT 1000000,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Orders Table
```sql
CREATE TABLE orders (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  symbol VARCHAR(50) NOT NULL,
  quantity INT NOT NULL,
  price FLOAT NOT NULL,
  total_amount FLOAT NOT NULL,
  side ENUM('BUY', 'SELL') NOT NULL,
  status ENUM('PENDING', 'COMPLETED', 'CANCELLED', 'FAILED') DEFAULT 'COMPLETED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_user_id (user_id),
  INDEX idx_symbol (symbol)
);
```

### Positions Table
```sql
CREATE TABLE positions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  symbol VARCHAR(50) NOT NULL,
  quantity INT DEFAULT 0,
  average_price FLOAT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_user_symbol (user_id, symbol)
);
```

---

## 🔥 Performance Considerations

- **Redis for Prices**: All prices fetched from Redis (O(1) lookup)
- **Database Indexing**: Proper indexes on user_id, symbol, created_at
- **Connection Pooling**: SQLAlchemy handles connection optimization
- **Async Operations**: All I/O operations are non-blocking
- **WebSocket Broadcasting**: Efficient connection management
- **Background Tasks**: Price updates run independently without blocking API

---

## 🧪 Testing the API

### Using Python Requests
```python
import requests

# Create user
resp = requests.post(
    'http://localhost:8000/users',
    json={'name': 'Test User', 'email': 'test@example.com'}
)
user_id = resp.json()['id']

# Get portfolio
resp = requests.get(f'http://localhost:8000/portfolio/{user_id}')
print(resp.json())

# Place order
resp = requests.post(
    'http://localhost:8000/orders',
    json={
        'user_id': user_id,
        'symbol': 'SBIN',
        'qty': 5,
        'side': 'BUY'
    }
)
print(resp.json())
```

### Using WebSocket Client
```python
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect('ws://localhost:8000/ws/1') as ws:
        while True:
            message = await ws.recv()
            print(json.loads(message))

asyncio.run(connect())
```

---

## 🚀 Production Deployment

### Environment Variables (Production)
```env
DEBUG=False
SECRET_KEY=<use-strong-random-key>
DB_URL=mysql+pymysql://prod_user:strong_password@prod_db_host/trading_db
REDIS_URL=redis://prod_redis_host:6379
```

### Using Docker

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Run with Docker Compose:**
```bash
docker-compose up -d
```

---

## 📝 Code Quality

- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ Error handling and validation
- ✅ Logging for debugging
- ✅ Clean, modular architecture
- ✅ SOLID principles followed
- ✅ Production-ready code

---

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Redis Documentation](https://redis.io/documentation)
- [WebSocket in FastAPI](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## ✨ Key Highlights

This implementation demonstrates:

1. **Production-Ready Architecture** - Modular, scalable, and maintainable
2. **Real-Time Capabilities** - WebSocket, Redis integration
3. **Proper Error Handling** - Validation, exception handling
4. **Clean Code** - Type hints, docstrings, logging
5. **Database Design** - Proper schema, relationships, indexing
6. **API Best Practices** - RESTful endpoints, Swagger documentation
7. **Business Logic** - Order execution, P&L calculations, position management
8. **Performance** - Async operations, Redis caching, connection pooling

---

**Built with ❤️ for production trading systems**
