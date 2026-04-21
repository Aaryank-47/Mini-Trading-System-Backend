# Trading Platform Backend

A FastAPI backend for a mini trading platform with JWT authentication, Redis-backed live market prices, instant order execution, portfolio tracking, and WebSocket updates.

## Highlights

- User registration and login with access and refresh tokens
- Authenticated portfolio, order, and profile endpoints
- Redis-backed market prices updated every second
- Instant BUY and SELL execution with atomic wallet and position updates
- Weighted average position pricing
- Real-time WebSocket notifications for price updates and executed orders

## Tech Stack

- FastAPI
- SQLAlchemy
- MySQL
- Redis
- Python-JOSE JWT
- SlowAPI rate limiting

## Project Layout

```text
Ts-backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── routers/
│   │   ├── users.py
│   │   ├── orders.py
│   │   ├── portfolio.py
│   │   └── market.py
│   ├── services/
│   ├── schemas/
│   ├── security/
│   ├── utils/
│   └── websocket/
├── tests/
├── README.md
├── MANUAL_TESTING_GUIDE.md
├── requirements.txt
└── requirements-test.txt
```

## Setup

### Prerequisites

- Python 3.10+
- MySQL 8+
- Redis 6+

### Install Dependencies

```bash
cd c:\Project\TradingSys\Ts-backend
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file with the following values:

```env
APP_NAME=Trading Platform API
DEBUG=True
SECRET_KEY=change-this-in-production

MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=trading_db
DB_URL=mysql+pymysql://root:password@localhost/trading_db

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379
```

### Start Services

```bash
redis-server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Open API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Overview

### Health

- `GET /health`
- `GET /health/quick`
- `GET /health/redis`
- `GET /health/database`
- `GET /health/metrics`
- `POST /redis/reconnect`

### Users

#### Register

`POST /users/register`

Request:

```json
{
  "name": "Trader One",
  "email": "trader@example.com",
  "password": "Testing@234",
  "confirm_password": "Testing@234"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_id": 1
}
```

#### Login

`POST /users/login`

Request:

```json
{
  "email": "trader@example.com",
  "password": "Testing@234"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "user_id": 1,
  "expires_in": 1800
}
```

#### Refresh Access Token

`POST /users/token/refresh`

Request:

```json
{
  "refresh_token": "<refresh-token>"
}
```

#### Protected User Endpoints

- `GET /users/profile`
- `GET /users/{user_id}`
- `GET /users?skip=0&limit=50`
- `DELETE /users/{user_id}`

These endpoints require `Authorization: Bearer <access_token>`.

### Market

- `GET /market/prices`
- `GET /market/price/{symbol}`

Prices are stored in Redis using keys like `price:SBIN` and updated every second.

### Orders

#### Place Order

`POST /orders`

Request:

```json
{
  "user_id": 1,
  "symbol": "SBIN",
  "qty": 10,
  "side": "BUY"
}
```

Notes:

- `side` must be `BUY` or `SELL`
- Orders execute immediately with status `COMPLETED`
- BUY orders deduct wallet balance and update positions
- SELL orders validate quantity, reduce positions, and credit the wallet

#### Order History

- `GET /orders/{user_id}`
- `GET /orders/{user_id}/count`

### Portfolio

- `GET /portfolio/{user_id}`
- `GET /portfolio/{user_id}/positions`
- `GET /portfolio/{user_id}/balance`

`/portfolio/{user_id}/positions` returns current holdings with weighted average price, current price, total invested, current value, unrealized P&L, and P&L percentage.

## WebSocket

### Connection

Use the WebSocket scheme, not `http://`:

```text
ws://localhost:8000/ws/{user_id}
```

Optional token:

```text
ws://localhost:8000/ws/{user_id}?token=<access_token>
```

If you open `http://localhost:8000/ws/1` in a browser or send a normal HTTP request, you will get `404 Not Found`. This route is WebSocket-only.

### Example Client

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/1');

ws.onopen = () => console.log('connected');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
ws.onclose = () => console.log('closed');
```

### WebSocket Events

#### Order Executed

```json
{
  "event": "order_executed",
  "symbol": "SBIN",
  "qty": 10,
  "price": 820.5,
  "side": "BUY",
  "status": "COMPLETED",
  "total_amount": 8205.0,
  "timestamp": "2026-04-21T17:32:23.492230"
}
```

#### Price Update

```json
{
  "event": "price_update",
  "symbol": "SBIN",
  "price": 1824.84,
  "timestamp": "2026-04-21T17:32:23.490975"
}
```

## Runtime Behavior

- Market prices are refreshed every second in a background task.
- Orders are executed atomically with database transactions.
- Positions use `Decimal` math to avoid precision loss.
- The app broadcasts `price_update` to all active WebSocket clients.
- The app broadcasts `order_executed` to the matching user connection.

## Manual Testing

For a complete step-by-step test flow, see [MANUAL_TESTING_GUIDE.md](./MANUAL_TESTING_GUIDE.md).

## Common Issues

- `Not authenticated`: user must register first, then login with the same email and password.
- `404` on `/ws/{user_id}`: use `ws://`, not `http://`.
- Missing price: make sure Redis is running and the price update task is active.
- Insufficient balance or quantity: verify the account state in `/portfolio/{user_id}` and `/orders/{user_id}`.

## Notes

- Protected endpoints use JWT bearer authentication.
- The API supports Swagger and WebSocket testing side by side.
- This backend is designed to run with the companion frontend in the workspace.
