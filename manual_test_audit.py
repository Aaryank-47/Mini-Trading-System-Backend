import requests
import json
import uuid

BASE_URL = "http://localhost:8001"

def print_step(title, method, url, request_body=None, response=None):
    print(f"\n{'='*50}")
    print(f"STEP: {title}")
    print(f"{'='*50}")
    print(f"REQUEST:")
    print(f"  {method} {url}")
    if request_body:
        print(f"  Body: {json.dumps(request_body, indent=2)}")
    print(f"\nRESPONSE:")
    if response is not None:
        print(f"  Status: {response.status_code}")
        try:
            print(f"  Body: {json.dumps(response.json(), indent=2)}")
        except Exception:
            print(f"  Body: {response.text}")
    else:
        print("  No Response provided")
    print("\n")

def run_tests():
    # 1. Register
    email = f"audit_tester_{uuid.uuid4().hex[:8]}@test.com"
    register_body = {
        "name": "Audit Tester",
        "email": email,
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!"
    }
    resp = requests.post(f"{BASE_URL}/users/register", json=register_body)
    print_step("1. Register User", "POST", "/users/register", register_body, resp)
    
    # 2. Login
    login_body = {
        "email": email,
        "password": "TestPassword123!"
    }
    resp = requests.post(f"{BASE_URL}/users/login", json=login_body)
    print_step("2. Login User", "POST", "/users/login", login_body, resp)
    
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Add Funds (Wallet Credit)
    deposit_body = {"amount": 1000.0}
    resp = requests.post(f"{BASE_URL}/portfolio/wallet/deposit", json=deposit_body, headers=headers)
    print_step("3. Deposit Funds", "POST", "/portfolio/wallet/deposit", deposit_body, resp)
    
    # 4. Fetch Audit Logs
    resp = requests.get(f"{BASE_URL}/audit-logs?size=10", headers=headers)
    print_step("4. Fetch Audit Logs", "GET", "/audit-logs", None, resp)

if __name__ == "__main__":
    run_tests()
