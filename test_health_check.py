#!/usr/bin/env python3
"""
Health Check Endpoints Test Script

Tests all 8 health check endpoints to verify:
1. All endpoints are accessible (200 status)
2. Response structure is correct
3. Required fields are present
4. Response times are acceptable

Run: python test_health_check.py
"""

import requests
import json
import time
from typing import Dict, Any
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 10

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class HealthCheckTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{BLUE}{'='*60}")
        print(f"{text}")
        print(f"{'='*60}{RESET}\n")
    
    def print_pass(self, text: str):
        """Print success message"""
        print(f"{GREEN}✓ {text}{RESET}")
        self.passed += 1
    
    def print_fail(self, text: str):
        """Print failure message"""
        print(f"{RED}✗ {text}{RESET}")
        self.failed += 1
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{YELLOW}ℹ {text}{RESET}")
    
    def test_endpoint(self, name: str, method: str, endpoint: str, 
                     expected_fields: list = None, max_time: float = 1.0) -> Dict[str, Any]:
        """Test a single endpoint"""
        print(f"\n{BLUE}Testing: {name}{RESET}")
        
        url = f"{self.base_url}{endpoint}"
        print(f"  URL: {method} {url}")
        
        try:
            start = time.time()
            
            if method.upper() == "GET":
                response = requests.get(url, timeout=TIMEOUT)
            elif method.upper() == "POST":
                response = requests.post(url, timeout=TIMEOUT)
            else:
                self.print_fail(f"Unknown method: {method}")
                return {}
            
            elapsed = time.time() - start
            
            # Check status code
            if response.status_code == 200:
                self.print_pass(f"Status code: {response.status_code}")
            else:
                self.print_fail(f"Status code: {response.status_code} (expected 200)")
                return {}
            
            # Check response time
            if elapsed < max_time:
                self.print_pass(f"Response time: {elapsed*1000:.2f}ms (limit: {max_time*1000:.0f}ms)")
            else:
                self.print_info(f"Response time: {elapsed*1000:.2f}ms (limit: {max_time*1000:.0f}ms)")
            
            # Parse JSON
            try:
                data = response.json()
                self.print_pass(f"Valid JSON response")
            except json.JSONDecodeError:
                self.print_fail(f"Invalid JSON response")
                return {}
            
            # Check expected fields
            if expected_fields:
                missing = [f for f in expected_fields if f not in data]
                if missing:
                    self.print_fail(f"Missing fields: {missing}")
                else:
                    self.print_pass(f"All expected fields present: {expected_fields}")
            
            # Print sample response
            print(f"  {YELLOW}Sample response (first 200 chars):{RESET}")
            response_str = json.dumps(data, indent=2)[:200]
            for line in response_str.split('\n'):
                print(f"    {line}")
            
            return data
            
        except requests.exceptions.ConnectionError:
            self.print_fail(f"Cannot connect to {self.base_url}")
            self.print_info("Make sure the server is running: python -m uvicorn app.main:app --reload")
            return {}
        except requests.exceptions.Timeout:
            self.print_fail(f"Request timeout (>{TIMEOUT}s)")
            return {}
        except Exception as e:
            self.print_fail(f"Error: {str(e)}")
            return {}
    
    def run_all_tests(self):
        """Run all health check tests"""
        self.print_header("HEALTH CHECK ENDPOINTS TEST SUITE")
        
        # Test 1: Overall health
        self.test_endpoint(
            "GET /health - Overall System Health",
            "GET",
            "/health",
            expected_fields=["status", "timestamp", "components"],
            max_time=0.1
        )
        
        # Test 2: Quick health
        self.test_endpoint(
            "GET /health/quick - Quick Status",
            "GET",
            "/health/quick",
            expected_fields=["status", "database", "redis"],
            max_time=0.05
        )
        
        # Test 3: Detailed health
        self.test_endpoint(
            "GET /health/detailed - Detailed Report",
            "GET",
            "/health/detailed",
            expected_fields=["timestamp", "summary", "application"],
            max_time=0.15
        )
        
        # Test 4: Database only
        self.test_endpoint(
            "GET /health/database - Database Status",
            "GET",
            "/health/database",
            expected_fields=["component", "status", "details"],
            max_time=0.05
        )
        
        # Test 5: Redis only
        self.test_endpoint(
            "GET /health/redis - Redis Status",
            "GET",
            "/health/redis",
            expected_fields=["component", "status", "connected"],
            max_time=0.05
        )
        
        # Test 6: Metrics
        self.test_endpoint(
            "GET /health/metrics - Server Metrics",
            "GET",
            "/health/metrics",
            expected_fields=["timestamp", "server_resources"],
            max_time=0.1
        )
        
        # Test 7: Redis detailed status
        self.test_endpoint(
            "GET /redis/status - Redis Details",
            "GET",
            "/redis/status",
            expected_fields=["connection_status", "details"],
            max_time=0.05
        )
        
        # Test 8: Manual reconnect
        self.test_endpoint(
            "POST /redis/reconnect - Force Reconnection",
            "POST",
            "/redis/reconnect",
            expected_fields=["success", "status"],
            max_time=0.15
        )
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"  {GREEN}Passed: {self.passed}{RESET}")
        print(f"  {RED}Failed: {self.failed}{RESET}")
        print(f"  Total: {total}")
        print(f"  Success Rate: {percentage:.1f}%")
        
        if self.failed == 0:
            print(f"\n  {GREEN}✓ All tests passed!{RESET}")
        else:
            print(f"\n  {RED}✗ Some tests failed!{RESET}")
        
        print(f"\n  Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def verify_server_running():
    """Verify server is running before tests"""
    print(f"\n{YELLOW}Checking if server is running at {BASE_URL}...{RESET}")
    try:
        response = requests.get(f"{BASE_URL}/health/quick", timeout=2)
        if response.status_code == 200:
            print(f"{GREEN}✓ Server is running!{RESET}\n")
            return True
    except:
        pass
    
    print(f"{RED}✗ Cannot connect to server at {BASE_URL}{RESET}")
    print(f"{YELLOW}To start the server, run:{RESET}")
    print(f"  cd Ts-backend")
    print(f"  python -m uvicorn app.main:app --reload")
    return False


def main():
    """Main entry point"""
    print(f"\n{BLUE}")
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Health Check Endpoints Test Suite                 ║")
    print("║   Testing 8 comprehensive health check endpoints    ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    
    # Verify server is running
    if not verify_server_running():
        return
    
    # Run tests
    tester = HealthCheckTester(BASE_URL)
    tester.run_all_tests()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
    except Exception as e:
        print(f"\n{RED}Test suite error: {e}{RESET}")
