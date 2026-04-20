# Trading Platform - Comprehensive Testing Guide

## Overview

This document explains how to run the complete test suite for the Trading Platform backend. The test suite includes unit tests, integration tests, security tests, service layer tests, and load testing.

**Total Test Cases: 50+**

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_users.py            # 9 tests for user endpoints
├── test_orders.py           # 25+ tests for order endpoints
├── test_portfolio.py        # 8 tests for portfolio endpoints
├── test_security.py         # 15+ tests for security
└── test_services.py         # 12+ tests for business logic
load_test.py                 # Load testing (100+ concurrent users)
run_tests.py                 # Test runner script with reporting
pytest.ini                   # Pytest configuration
requirements-test.txt        # Test dependencies
```

## Setup

### 1. Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

Or install individually:

```bash
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
pip install pytest-cov==4.1.0
pip install pytest-html==4.1.1
pip install aiohttp==3.9.1
pip install httpx==0.25.1
```

### 2. Database Setup

Tests use an in-memory SQLite database configured in `conftest.py`. No additional setup required.

## Running Tests

### Quick Start - Run All Tests

```bash
python run_tests.py
```

This runs the complete test suite with:
- All unit tests
- Coverage analysis
- HTML report generation
- Summary report

### Individual Test Suites

#### Run User Tests Only
```bash
pytest tests/test_users.py -v
```
**Coverage:** User registration, authentication, JWT tokens, profile access, rate limiting
**Tests:** 9 test cases

#### Run Order Tests Only
```bash
pytest tests/test_orders.py -v
```
**Coverage:** Order creation, validation, authorization, rate limiting, order history
**Tests:** 25+ test cases

#### Run Portfolio Tests Only
```bash
pytest tests/test_portfolio.py -v
```
**Coverage:** Portfolio retrieval, positions, market data, authorization checks
**Tests:** 8 test cases

#### Run Security Tests Only
```bash
pytest tests/test_security.py -v
```
**Coverage:** JWT validation, authorization, input validation, security headers
**Tests:** 15+ test cases

#### Run Service Layer Tests Only
```bash
pytest tests/test_services.py -v
```
**Coverage:** Wallet operations, position management, order execution, user management
**Tests:** 12+ test cases

### Running Specific Tests

```bash
# Run specific test class
pytest tests/test_users.py::TestUserRegistration -v

# Run specific test method
pytest tests/test_users.py::TestUserRegistration::test_register_user_success -v

# Run tests matching pattern
pytest tests/ -k "rate_limit" -v
```

### Test Options

```bash
# Verbose output
pytest tests/ -v

# Show print statements
pytest tests/ -s

# Stop on first failure
pytest tests/ -x

# Show slowest 10 tests
pytest tests/ --durations=10

# Run with specific markers
pytest tests/ -m security

# Generate HTML report
pytest tests/ --html=report.html

# Generate coverage report
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

## Load Testing

### Prerequisites

Ensure the backend is running:

```bash
python main.py
```

### Run Load Test

```bash
python load_test.py
```

**Configuration:**
- 100 concurrent users
- 10 orders per user
- 50 concurrent requests
- 30-second timeout

**Metrics Captured:**
- Response time (min, max, avg, median, std dev)
- Requests per second
- Success/failure rate
- Status code distribution

**Expected Results:**
- All requests should complete within 5 seconds
- No race conditions or data inconsistencies
- Database handles 1000+ concurrent operations

## Test Fixtures

All fixtures are defined in `conftest.py`:

### Database Fixtures
- **db**: SQLAlchemy session for tests
- **client**: FastAPI TestClient

### User Fixtures
- **test_user**: Sample user in test DB
- **test_user_token**: JWT token for test user
- **test_user_headers**: Authorization header
- **second_test_user**: Second test user
- **second_user_token**: JWT token for second user
- **second_user_headers**: Authorization header

### Data Fixtures
- **valid_order_data**: Valid order for testing
- **invalid_order_data**: Invalid order for testing

## Test Categories

### Unit Tests (40 tests)

Test individual components in isolation:

#### Users (9 tests)
- ✅ User registration success
- ✅ Duplicate email handling
- ✅ Invalid email validation
- ✅ Empty name validation
- ✅ XSS prevention in name
- ✅ Profile access (authenticated)
- ✅ Profile access (unauthenticated)
- ✅ Invalid token handling
- ✅ Rate limit enforcement (5/min)

#### Orders (25+ tests)
- ✅ Order creation (success)
- ✅ Order authentication
- ✅ Order authorization
- ✅ Quantity validation (negative, zero, max)
- ✅ Symbol validation (uppercase only)
- ✅ Side validation (BUY/SELL)
- ✅ Insufficient balance
- ✅ Rate limit enforcement (10/min)
- ✅ Order history retrieval
- ✅ Ownership verification
- ✅ Decimal precision

#### Portfolio (8 tests)
- ✅ Portfolio retrieval (authenticated)
- ✅ Portfolio access control
- ✅ Positions endpoint
- ✅ Market prices (public)
- ✅ Health check

#### Security (15+ tests)
- ✅ JWT token creation
- ✅ Invalid bearer token
- ✅ Missing bearer prefix
- ✅ Malformed JWT
- ✅ Email validation
- ✅ XSS prevention
- ✅ Symbol validation
- ✅ Quantity bounds
- ✅ Rate limiting bypass prevention
- ✅ Authorization checks

#### Services (12+ tests)
- ✅ Wallet deduction (success, insufficient funds)
- ✅ Balance addition
- ✅ Decimal precision
- ✅ Weighted average price calculation
- ✅ Position deletion on zero quantity
- ✅ BUY order execution
- ✅ SELL order validation
- ✅ Atomic transactions
- ✅ User creation with wallet
- ✅ User retrieval

### Performance Testing (Load Test)

**Configuration:**
- 100 users
- 1000 total requests
- Concurrent request limit: 50
- Timeout: 30 seconds

**Metrics:**
- Response time distribution
- Throughput (requests/second)
- Error rate
- Status code breakdown

## Expected Coverage

### Security Features Tested
- ✅ JWT authentication on all protected endpoints
- ✅ Authorization checks (user ownership verification)
- ✅ Input validation (all fields validated)
- ✅ XSS prevention (dangerous characters rejected)
- ✅ Rate limiting (per IP address)
- ✅ CORS configuration
- ✅ SQL injection prevention (parameterized queries)

### Business Logic Tested
- ✅ Wallet balance tracking
- ✅ Order execution (atomic transactions)
- ✅ Position management
- ✅ Decimal precision (no float precision loss)
- ✅ Concurrent operations (row-level locking)
- ✅ Market data updates

### Performance Tested
- ✅ Connection pooling (QueuePool)
- ✅ Database query performance
- ✅ Concurrent request handling
- ✅ Response time under load
- ✅ Memory usage

## Interpreting Results

### Successful Test Run
```
✅ PASSED - Unit Tests - Users
✅ PASSED - Unit Tests - Orders
✅ PASSED - Unit Tests - Portfolio
✅ PASSED - Unit Tests - Security
✅ PASSED - Unit Tests - Services
✅ PASSED - All Tests with HTML Report
✅ PASSED - Code Coverage Analysis

Total: 6 | Passed: 6 | Failed: 0
🎉 ALL TESTS PASSED! Backend is production-ready.
```

### Investigating Failures

1. **Check test output** for specific assertion failures
2. **Review error messages** for validation issues
3. **Check database state** in test logs
4. **Verify test data** in conftest.py fixtures
5. **Check for race conditions** in concurrent tests

## Coverage Reports

After running tests with coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

Open `htmlcov/index.html` in browser to view:
- Overall coverage percentage
- Per-file coverage
- Missing lines
- Branch coverage

**Target Coverage:**
- Services: 95%+
- Routes: 90%+
- Models: 100%
- Schemas: 100%

## CI/CD Integration

To integrate into CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest tests/ --cov=app --cov-report=xml
    python load_test.py

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Best Practices

### Writing New Tests
1. Use descriptive test names
2. One assertion per test (when possible)
3. Use fixtures for setup/teardown
4. Test both success and failure paths
5. Verify error messages

### Running Tests
1. Run full suite before committing
2. Fix failing tests immediately
3. Review coverage reports
4. Run load test before deployment
5. Monitor test execution time

### Maintenance
1. Keep tests updated with code changes
2. Remove obsolete tests
3. Refactor duplicated test code
4. Add tests for new features
5. Review test performance

## Troubleshooting

### Import Errors
```
ModuleNotFoundError: No module named 'app'
```
**Solution:** Run pytest from project root directory

### Database Lock Errors
```
sqlite3.OperationalError: database is locked
```
**Solution:** Ensure tests clean up properly, check conftest.py cleanup

### Timeout Errors
```
asyncio.TimeoutError
```
**Solution:** Increase timeout or check backend performance

### Rate Limit Not Triggering
```
Expected 429, got 201
```
**Solution:** Rate limiter may reset between tests, verify test isolation

## Performance Benchmarks

Expected response times (P50/P95/P99):
- User registration: 50ms / 100ms / 200ms
- Order creation: 100ms / 200ms / 500ms
- Portfolio retrieval: 50ms / 100ms / 150ms
- Order history: 50ms / 100ms / 200ms

Expected throughput:
- 1000+ requests/second for read operations
- 500+ requests/second for write operations
- 100+ concurrent users without degradation

## Next Steps

1. ✅ Run all tests: `python run_tests.py`
2. ✅ Check coverage report
3. ✅ Run load test: `python load_test.py`
4. ✅ Review HTML test report
5. ✅ Deploy with confidence

## Support

For test-related issues:
1. Check test output for specific failures
2. Review fixture setup in conftest.py
3. Verify test database isolation
4. Check for timing-dependent tests
5. Review error messages carefully

---

**Last Updated:** 2024
**Total Test Cases:** 50+
**Estimated Runtime:** 2-3 minutes (unit tests)
**Load Test Duration:** 5-10 minutes
