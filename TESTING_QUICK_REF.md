# Testing Quick Reference

## One-Command Test Everything

```bash
python run_tests.py
```

## Individual Test Suites

```bash
# User registration & authentication
pytest tests/test_users.py -v

# Order creation & management
pytest tests/test_orders.py -v

# Portfolio & positions
pytest tests/test_portfolio.py -v

# Security & authorization
pytest tests/test_security.py -v

# Business logic (services)
pytest tests/test_services.py -v

# End-to-end workflows
pytest tests/test_integration.py -v
```

## Load Testing (Backend Must Be Running)

```bash
# In terminal 1: Start backend
python main.py

# In terminal 2: Run load test
python load_test.py
```

## Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=app --cov-report=html

# Open in browser (Windows)
start htmlcov/index.html

# Open in browser (Mac/Linux)
open htmlcov/index.html
```

## Run Specific Tests

```bash
# Single test file
pytest tests/test_users.py -v

# Single test class
pytest tests/test_users.py::TestUserRegistration -v

# Single test method
pytest tests/test_users.py::TestUserRegistration::test_register_user_success -v

# Tests matching pattern
pytest tests/ -k "rate_limit" -v
```

## Test Markers

```bash
# Security tests only
pytest tests/ -m security

# Unit tests only
pytest tests/ -m unit

# Performance tests
pytest tests/ -m performance
```

## Debugging Tests

```bash
# Show print statements
pytest tests/test_users.py -s

# Stop on first failure
pytest tests/test_users.py -x

# Show local variables on failure
pytest tests/test_users.py -l

# Drop into debugger on failure
pytest tests/test_users.py --pdb
```

## Test Statistics

```bash
# Show slowest tests
pytest tests/ --durations=10

# Show test names only (no output)
pytest tests/ -q

# Show test collection
pytest tests/ --collect-only
```

## Dependencies Check

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Verify installation
python -c "import pytest; import pytest_cov; print('✅ All test dependencies installed')"
```

## Expected Output

### Successful Run
```
================================ test session starts =================================
platform win32 -- Python 3.11.x, pytest-7.4.3, pluggy-1.1.1
rootdir: c:\Project\TradingSys\Ts-backend
collected 50 items

tests/test_users.py::TestUserRegistration::test_register_user_success PASSED    [  2%]
tests/test_users.py::TestUserRegistration::test_register_user_duplicate_email PASSED [  4%]
...
tests/test_security.py::TestSecurityHeaders::test_x_content_type_options_header PASSED [98%]

========================== 50 passed in 12.45s ==================================
```

### Coverage Summary
```
Name                    Stmts   Miss  Cover
-------------------------------------------
app/services/wallet.py    45      2    96%
app/services/order.py     78      3    96%
app/routers/orders.py     62      4    93%
-------------------------------------------
TOTAL                    185      9    95%
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Run pytest from project root |
| Database locked | Wait a moment and retry |
| Rate limit test fails | Test isolation issue, check conftest |
| Timeout errors | Increase timeout or check backend |
| Token validation fails | Ensure SECRET_KEY matches |

## Before Deployment

- [ ] `pytest tests/ -v` - All tests passing
- [ ] `pytest tests/ --cov=app` - Coverage > 90%
- [ ] `python load_test.py` - Load test successful
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] All security headers present
- [ ] Rate limiting working
- [ ] Database transactions atomic

## Files

```
conftest.py              # Test fixtures & configuration
run_tests.py             # Automated test runner with reporting
load_test.py             # Load testing script
pytest.ini               # Pytest configuration
requirements-test.txt    # Test dependencies
README_TESTING.md        # Comprehensive testing guide
TESTING_QUICK_REF.md     # This file
```

---

**Last Updated:** 2024  
**Total Tests:** 50+  
**Average Runtime:** 2-3 minutes
