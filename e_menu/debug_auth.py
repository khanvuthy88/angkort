#!/usr/bin/env python3
"""
Debug script for authentication endpoints.

This script helps identify issues with the authentication API endpoints.
"""

import requests
import json

def test_endpoint(url, method="GET", data=None, headers=None):
    """Test an endpoint and print detailed information."""
    print(f"\n🔍 Testing: {method} {url}")
    print(f"📋 Headers: {headers or {}}")
    if data:
        print(f"📤 Data: {data}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            print(f"❌ Unsupported method: {method}")
            return
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"📥 JSON Response: {json.dumps(response_json, indent=2)}")
        except json.JSONDecodeError:
            print(f"📥 Text Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Main debug function."""
    base_url = "http://localhost:8069"
    
    print("🐛 Debug Authentication Endpoints")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("\n1️⃣ Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/web")
        print(f"✅ Server is running. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {str(e)}")
        print("💡 Make sure Odoo server is running on localhost:8069")
        return
    
    # Test 1.5: Test the simple HTTP test endpoint
    print("\n1️⃣.5️⃣ Testing simple HTTP endpoint...")
    test_url = f"{base_url}/api/test"
    
    # Test GET request
    test_endpoint(test_url, "GET")
    
    # Test POST request with JSON
    test_data = {"test": "data", "number": 123}
    test_endpoint(test_url, "POST", test_data, {"Content-Type": "application/json"})
    
    # Test POST request with form data
    form_data = {"test": "data", "number": "123"}
    test_endpoint(test_url, "POST", form_data, {"Content-Type": "application/x-www-form-urlencoded"})
    
    # Test 2: Test login endpoint
    print("\n2️⃣ Testing login endpoint...")
    login_url = f"{base_url}/api/login"
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    login_headers = {
        "Content-Type": "application/json"
    }
    
    test_endpoint(login_url, "POST", login_data, login_headers)
    
    # Test 3: Test with different content types
    print("\n3️⃣ Testing with form data...")
    form_headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    form_data = "username=admin&password=admin"
    
    try:
        response = requests.post(login_url, data=form_data, headers=form_headers)
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 4: Test refresh endpoint
    print("\n4️⃣ Testing refresh endpoint...")
    refresh_url = f"{base_url}/api/refresh"
    refresh_data = {
        "refresh_token": "test_token"
    }
    
    test_endpoint(refresh_url, "POST", refresh_data, login_headers)
    
    # Test 5: Test logout endpoint
    print("\n5️⃣ Testing logout endpoint...")
    logout_url = f"{base_url}/api/logout"
    logout_headers = {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    }
    
    test_endpoint(logout_url, "POST", headers=logout_headers)
    
    print("\n✅ Debug tests completed!")

if __name__ == "__main__":
    main()
