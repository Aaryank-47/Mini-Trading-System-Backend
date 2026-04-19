# Trading Platform API - Complete Postman Test Guide

**Base URL:** `http://localhost:8000`

**Available Symbols:** `SBIN`, `RELIANCE`, `TCS`, `INFY`, `HDFC`

---

## 📋 Table of Contents
1. [Users API](#users-api)
2. [Orders API](#orders-api)
3. [Portfolio API](#portfolio-api)
4. [Market API](#market-api)
5. [WebSocket Connections](#websocket-connections)

---

## 🔷 USERS API

### 1. Create User
**Endpoint:** `POST /users`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Aaryan Kumar",
  "email": "aaryan@example.com"
}
```

**Success Response (201):**
```json
{
  "id": 1,
  "name": "Aaryan Kumar",
  "email": "aaryan@example.com",
  "created_at": "2026-04-19T14:15:00.000Z",
  "updated_at": "2026-04-19T14:15:00.000Z"
}
```

**Error Response (400) - Duplicate Email:**
```json
{
  "detail": "User with this email already exists"
}
```

**Error Response (500) - Server Error:**
```json
{
  "detail": "Failed to create user"
}
```

**Test Cases:**
- ✅ Create with valid name and email
- ❌ Duplicate email
- ❌ Missing email field
- ❌ Invalid email format
- ❌ Empty name

---

### 2. Get User Details
**Endpoint:** `GET /users/{user_id}`

**URL:** `http://localhost:8000/users/1`

**Response (200):**
```json
{
  "id": 1,
  "name": "Aaryan Kumar",
  "email": "aaryan@example.com",
  "created_at": "2026-04-19T14:15:00.000Z",
  "updated_at": "2026-04-19T14:15:00.000Z"
}
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Get valid user
- ❌ Get non-existent user (ID: 999)
- ❌ Invalid user ID (string instead of integer)

---

### 3. Get All Users (Pagination)
**Endpoint:** `GET /users?skip=0&limit=10`

**URL:** `http://localhost:8000/users?skip=0&limit=10`

**Query Parameters:**
- `skip` (optional): Number of users to skip (default: 0)
- `limit` (optional): Number of users to return (default: 100)

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Aaryan Kumar",
    "email": "aaryan@example.com",
    "created_at": "2026-04-19T14:15:00.000Z",
    "updated_at": "2026-04-19T14:15:00.000Z"
  },
  {
    "id": 2,
    "name": "John Doe",
    "email": "john@example.com",
    "created_at": "2026-04-19T14:20:00.000Z",
    "updated_at": "2026-04-19T14:20:00.000Z"
  }
]
```

**Test Cases:**
- ✅ Get all users with default pagination
- ✅ Get with custom skip and limit
- ✅ Get with skip=0, limit=1
- ✅ Get with large limit

---

### 4. Delete User
**Endpoint:** `DELETE /users/{user_id}`

**URL:** `http://localhost:8000/users/1`

**Response (204) - No Content:**
```
(Empty body)
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Delete existing user
- ❌ Delete non-existent user
- ❌ Delete same user twice

---

## 🔷 ORDERS API

### 1. Create Order (BUY/SELL)
**Endpoint:** `POST /orders`

**Headers:**
```
Content-Type: application/json
```

**BUY Request Body:**
```json
{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 10,
  "side": "BUY"
}
```

**SELL Request Body:**
```json
{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 5,
  "side": "SELL"
}
```

**Success Response (201):**
```json
{
  "id": 1,
  "user_id": 1,
  "symbol": "SBIN",
  "quantity": 10,
  "price": 450.75,
  "total_amount": 4507.50,
  "side": "BUY",
  "status": "COMPLETED",
  "created_at": "2026-04-19T14:15:30.000Z",
  "updated_at": "2026-04-19T14:15:30.000Z"
}
```

**Error Response (400) - Insufficient Balance:**
```json
{
  "detail": "Insufficient wallet balance",
  "error_code": "VALIDATION_ERROR"
}
```

**Error Response (400) - Insufficient Quantity (SELL):**
```json
{
  "detail": "Insufficient quantity to sell",
  "error_code": "VALIDATION_ERROR"
}
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Error Response (400) - Invalid Side:**
```json
{
  "detail": "Invalid side. Must be BUY or SELL"
}
```

**Test Cases:**
- ✅ BUY order with valid data
- ✅ SELL order with valid data
- ❌ BUY with insufficient balance
- ❌ SELL with insufficient quantity
- ❌ Invalid side (not BUY/SELL)
- ❌ Negative quantity
- ❌ User doesn't exist
- ❌ Invalid symbol

---

### 2. Get Order History
**Endpoint:** `GET /orders/{user_id}?skip=0&limit=50`

**URL:** `http://localhost:8000/orders/1?skip=0&limit=50`

**Query Parameters:**
- `skip` (optional): Number of orders to skip (default: 0)
- `limit` (optional): Number of orders to return (default: 50)

**Response (200):**
```json
[
  {
    "id": 1,
    "symbol": "SBIN",
    "quantity": 10,
    "price": 450.75,
    "total_amount": 4507.50,
    "side": "BUY",
    "status": "COMPLETED",
    "created_at": "2026-04-19T14:15:30.000Z"
  },
  {
    "id": 2,
    "symbol": "RELIANCE",
    "quantity": 5,
    "price": 2850.50,
    "total_amount": 14252.50,
    "side": "BUY",
    "status": "COMPLETED",
    "created_at": "2026-04-19T14:20:30.000Z"
  }
]
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Get order history with default pagination
- ✅ Get with custom skip and limit
- ✅ Get orders for user with no history (empty array)
- ❌ Get orders for non-existent user

---

### 3. Get Order Count
**Endpoint:** `GET /orders/{user_id}/count`

**URL:** `http://localhost:8000/orders/1/count`

**Response (200):**
```json
{
  "user_id": 1,
  "total_orders": 15
}
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Get order count for user with orders
- ✅ Get order count for user with no orders
- ❌ Get count for non-existent user

---

## 🔷 PORTFOLIO API

### 1. Get Complete Portfolio
**Endpoint:** `GET /portfolio/{user_id}`

**URL:** `http://localhost:8000/portfolio/1`

**Response (200):**
```json
{
  "user_id": 1,
  "wallet_balance": 850000.50,
  "holdings": [
    {
      "symbol": "SBIN",
      "quantity": 10,
      "average_price": 450.75,
      "current_price": 455.20,
      "total_invested": 4507.50,
      "current_value": 4552.00,
      "unrealized_pnl": 44.50,
      "pnl_percentage": 0.99
    },
    {
      "symbol": "RELIANCE",
      "quantity": 5,
      "average_price": 2850.50,
      "current_price": 2875.00,
      "total_invested": 14252.50,
      "current_value": 14375.00,
      "unrealized_pnl": 122.50,
      "pnl_percentage": 0.86
    }
  ],
  "total_portfolio_value": 1768929.50,
  "total_invested": 18760.00,
  "total_unrealized_pnl": 167.00,
  "total_pnl_percentage": 0.89
}
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Get portfolio for user with holdings
- ✅ Get portfolio for user with no holdings (empty holdings array)
- ❌ Get portfolio for non-existent user

---

### 2. Get User Positions
**Endpoint:** `GET /portfolio/{user_id}/positions`

**URL:** `http://localhost:8000/portfolio/1/positions`

**Response (200):**
```json
[
  {
    "symbol": "SBIN",
    "quantity": 10,
    "average_price": 450.75,
    "current_price": 455.20,
    "total_invested": 4507.50,
    "current_value": 4552.00,
    "unrealized_pnl": 44.50,
    "pnl_percentage": 0.99
  },
  {
    "symbol": "TCS",
    "quantity": 2,
    "average_price": 3250.00,
    "current_price": 3280.50,
    "total_invested": 6500.00,
    "current_value": 6561.00,
    "unrealized_pnl": 61.00,
    "pnl_percentage": 0.94
  }
]
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Get positions for user with open positions
- ✅ Get positions for user with no positions (empty array)
- ❌ Get positions for non-existent user

---

### 3. Get Wallet Balance
**Endpoint:** `GET /portfolio/{user_id}/balance`

**URL:** `http://localhost:8000/portfolio/1/balance`

**Response (200):**
```json
{
  "user_id": 1,
  "balance": 850000.50,
  "currency": "INR"
}
```

**Error Response (404) - User Not Found:**
```json
{
  "detail": "User 999 not found"
}
```

**Test Cases:**
- ✅ Get balance for existing user
- ✅ Get balance for user with initial balance
- ❌ Get balance for non-existent user

---

## 🔷 MARKET API

### 1. Get All Prices
**Endpoint:** `GET /market/prices`

**URL:** `http://localhost:8000/market/prices`

**Response (200):**
```json
{
  "SBIN": 450.75,
  "RELIANCE": 2850.50,
  "TCS": 3250.00,
  "INFY": 1620.30,
  "HDFC": 2750.80
}
```

**Error Response (503) - Service Unavailable:**
```json
{
  "detail": "No prices available. Price service may not be running."
}
```

**Test Cases:**
- ✅ Get all prices (Redis running)
- ❌ Get all prices (Redis not running) - Returns 503
- ✅ Verify all default symbols present

---

### 2. Get Specific Symbol Price
**Endpoint:** `GET /market/price/{symbol}`

**URL:** `http://localhost:8000/market/price/SBIN`

**Path Parameters:**
- `symbol`: Stock symbol (e.g., SBIN, RELIANCE, TCS, INFY, HDFC)

**Response (200):**
```json
{
  "symbol": "SBIN",
  "price": 450.75
}
```

**Error Response (404) - Symbol Not Found:**
```json
{
  "detail": "Price not found for symbol INVALID"
}
```

**Test Cases:**
- ✅ Get price for SBIN
- ✅ Get price for RELIANCE
- ✅ Get price for TCS
- ✅ Get price for INFY
- ✅ Get price for HDFC
- ❌ Get price for invalid symbol
- ✅ Case insensitive (sbin, Sbin should work)

---

### 3. Market Health Check
**Endpoint:** `GET /market/health`

**URL:** `http://localhost:8000/market/health`

**Response (200) - Healthy:**
```json
{
  "status": "healthy",
  "available_symbols": 5
}
```

**Response (200) - Degraded:**
```json
{
  "status": "degraded",
  "available_symbols": 0
}
```

**Response (200) - Unhealthy:**
```json
{
  "status": "unhealthy",
  "error": "Error message describing the issue"
}
```

**Test Cases:**
- ✅ Check health (Redis running)
- ✅ Check health (Redis not running)
- ✅ Verify symbol count

---

## 🔷 WEBSOCKET CONNECTIONS

### Order Execution Notifications
**WebSocket URL:** `ws://localhost:8000/ws/orders/{user_id}`

**Connection Example:**
```
ws://localhost:8000/ws/orders/1
```

**Message Received After Order:**
```json
{
  "event": "order_executed",
  "symbol": "SBIN",
  "qty": 10,
  "price": 450.75,
  "side": "BUY",
  "status": "COMPLETED",
  "total_amount": 4507.50,
  "timestamp": "2026-04-19T14:15:30.000Z"
}
```

**Test Cases:**
- ✅ Connect to WebSocket
- ✅ Place order and verify WebSocket notification
- ✅ Multiple WebSocket connections
- ✅ Disconnect and reconnect

---

## 🔷 COMPLETE TEST SEQUENCE

### Scenario: New Trading User Journey

**Step 1: Create User**
```
POST /users
{
  "name": "Raj Patel",
  "email": "raj.patel@example.com"
}
```
✅ Save user_id = 1 and initial balance = ₹10,00,000

**Step 2: Check Wallet Balance**
```
GET /portfolio/1/balance
```
✅ Verify balance is ₹10,00,000

**Step 3: Get Market Prices**
```
GET /market/prices
```
✅ Save SBIN price = 450.75

**Step 4: Place BUY Order**
```
POST /orders
{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 100,
  "side": "BUY"
}
```
✅ Order completed, verify deducted balance

**Step 5: Check Updated Portfolio**
```
GET /portfolio/1
```
✅ Verify holdings contain 100 SBIN
✅ Verify wallet balance reduced

**Step 6: View Order History**
```
GET /orders/1
```
✅ Verify BUY order appears in history

**Step 7: Place SELL Order (Partial)**
```
POST /orders
{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 30,
  "side": "SELL"
}
```
✅ SELL successful, balance increased

**Step 8: Final Portfolio Check**
```
GET /portfolio/1
```
✅ Verify position reduced to 70 SBIN
✅ Verify P&L calculation

---

## 📝 POSTMAN COLLECTION SETUP

### Import Instructions:
1. Open Postman
2. Create a new Collection: "Trading Platform API"
3. Add folders for: Users, Orders, Portfolio, Market, WebSocket
4. For each API endpoint, create:
   - Request with proper method, URL, headers, body
   - Pre-request script (if needed for variables)
   - Tests (validation scripts)

### Environment Variables:
```
{
  "base_url": "http://localhost:8000",
  "user_id": 1,
  "symbol": "SBIN",
  "quantity": 10,
  "side": "BUY"
}
```

---

## ✅ VALIDATION CHECKLIST

- [ ] All 13 API endpoints tested
- [ ] Success responses verified
- [ ] Error responses (400, 404, 500, 503) tested
- [ ] All required parameters validated
- [ ] Response schema matches documentation
- [ ] Database constraints verified
- [ ] Business logic tested (balance deduction, position updates)
- [ ] Pagination working correctly
- [ ] P&L calculations accurate
- [ ] WebSocket notifications working
- [ ] Case sensitivity handled correctly
- [ ] Duplicate prevention working (email, user_symbol)
- [ ] Concurrent requests handled

---

## 🔗 USEFUL LINKS

- **API Documentation:** `http://localhost:8000/docs` (Swagger UI)
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`

---

**Last Updated:** April 19, 2026
**API Version:** 1.0.0
**Status:** ✅ Ready for Testing
