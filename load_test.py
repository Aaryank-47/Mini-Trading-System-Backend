"""
Load testing script for the Trading Platform
Tests performance under concurrent load
"""
import asyncio
import time
import statistics
from typing import List, Dict
import aiohttp
import json


class LoadTestConfig:
    """Load testing configuration"""
    BASE_URL = "http://localhost:8000"
    NUM_USERS = 100
    ORDERS_PER_USER = 10
    CONCURRENT_REQUESTS = 50
    TIMEOUT = 30


class LoadTestResult:
    """Store load test results"""
    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self.errors: List[str] = []
        self.start_time = time.time()
        self.end_time = None
    
    def add_response(self, response_time: float, status_code: int):
        """Record a response"""
        self.response_times.append(response_time)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def add_error(self, error: str):
        """Record an error"""
        self.errors.append(error)
    
    def finalize(self):
        """Finalize results and calculate stats"""
        self.end_time = time.time()
    
    def print_report(self):
        """Print load test report"""
        duration = self.end_time - self.start_time
        total_requests = len(self.response_times) + len(self.errors)
        
        print("\n" + "="*60)
        print("LOAD TEST REPORT")
        print("="*60)
        print(f"\nTest Duration: {duration:.2f} seconds")
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {len(self.response_times)}")
        print(f"Failed Requests: {len(self.errors)}")
        print(f"Requests/Second: {total_requests/duration:.2f}")
        
        if self.response_times:
            print(f"\nResponse Time Statistics:")
            print(f"  Min: {min(self.response_times)*1000:.2f}ms")
            print(f"  Max: {max(self.response_times)*1000:.2f}ms")
            print(f"  Avg: {statistics.mean(self.response_times)*1000:.2f}ms")
            print(f"  Median: {statistics.median(self.response_times)*1000:.2f}ms")
            print(f"  StdDev: {statistics.stdev(self.response_times)*1000:.2f}ms")
        
        print(f"\nStatus Code Distribution:")
        for code, count in sorted(self.status_codes.items()):
            print(f"  {code}: {count}")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors[:5]:  # Print first 5
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")
        
        print("\n" + "="*60 + "\n")


class LoadTester:
    """Load testing client"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.result = LoadTestResult()
        self.tokens = {}  # user_id -> JWT token
    
    async def register_user(self, session: aiohttp.ClientSession, user_id: int) -> str:
        """Register a user and return JWT token"""
        try:
            url = f"{self.config.BASE_URL}/users/register"
            data = {
                "name": f"LoadTest User {user_id}",
                "email": f"user{user_id}@loadtest.com"
            }
            
            start = time.time()
            async with session.post(url, json=data, timeout=self.config.TIMEOUT) as response:
                elapsed = time.time() - start
                
                self.result.add_response(elapsed, response.status)
                
                if response.status == 201:
                    json_data = await response.json()
                    return json_data.get("access_token")
                else:
                    self.result.add_error(f"Failed to register user {user_id}: {response.status}")
                    return None
        except Exception as e:
            self.result.add_error(f"Error registering user {user_id}: {str(e)}")
            return None
    
    async def create_order(self, session: aiohttp.ClientSession, user_id: int, token: str) -> bool:
        """Create a random order"""
        try:
            url = f"{self.config.BASE_URL}/orders"
            headers = {"Authorization": f"Bearer {token}"}
            data = {
                "user_id": user_id,
                "symbol": "SBIN",
                "qty": 10,
                "side": "BUY"
            }
            
            start = time.time()
            async with session.post(url, json=data, headers=headers, timeout=self.config.TIMEOUT) as response:
                elapsed = time.time() - start
                
                self.result.add_response(elapsed, response.status)
                
                if response.status != 201:
                    self.result.add_error(f"Order creation failed: {response.status}")
                    return False
                return True
        except Exception as e:
            self.result.add_error(f"Error creating order: {str(e)}")
            return False
    
    async def test_registration_load(self):
        """Test registration endpoint under load"""
        print(f"Testing registration with {self.config.NUM_USERS} users...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(self.config.NUM_USERS):
                task = self.register_user(session, i)
                tasks.append(task)
            
            tokens = await asyncio.gather(*tasks)
            self.tokens = {i: tokens[i] for i in range(self.config.NUM_USERS) if tokens[i]}
        
        print(f"Successfully registered {len(self.tokens)} users")
    
    async def test_order_creation_load(self):
        """Test order creation under load"""
        print(f"Testing order creation with {self.config.NUM_USERS} users * {self.config.ORDERS_PER_USER} orders...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for user_id, token in self.tokens.items():
                for _ in range(self.config.ORDERS_PER_USER):
                    task = self.create_order(session, user_id, token)
                    tasks.append(task)
                
                # Control concurrency
                if len(tasks) >= self.config.CONCURRENT_REQUESTS:
                    await asyncio.gather(*tasks)
                    tasks = []
            
            # Execute remaining tasks
            if tasks:
                await asyncio.gather(*tasks)
    
    async def run_full_test(self):
        """Run complete load test"""
        print("Starting Load Test...\n")
        
        await self.test_registration_load()
        await self.test_order_creation_load()
        
        self.result.finalize()
        self.result.print_report()


async def main():
    """Run load tests"""
    config = LoadTestConfig()
    tester = LoadTester(config)
    
    try:
        await tester.run_full_test()
    except KeyboardInterrupt:
        print("\nLoad test interrupted by user")


if __name__ == "__main__":
    print("""
    🚀 TRADING PLATFORM LOAD TEST
    
    Configuration:
    - Number of Users: 100
    - Orders per User: 10
    - Concurrent Requests: 50
    - Timeout: 30 seconds
    
    Make sure the backend is running before starting the test!
    """)
    
    input("Press Enter to start load test...")
    
    asyncio.run(main())
