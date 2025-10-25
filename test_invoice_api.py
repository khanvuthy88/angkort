#!/usr/bin/env python3
"""
Test script for the new invoice API endpoints
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8069"  # Adjust as needed
USERNAME = "admin"  # Adjust as needed
PASSWORD = "admin"   # Adjust as needed
DATABASE = "your_database"  # Adjust as needed

def get_auth_token():
    """Get JWT token for authentication using existing auth system"""
    login_url = f"{BASE_URL}/angkort/api/v1/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        response.raise_for_status()
        data = response.json()
        if data.get('status'):
            return data['data']['access_token']
        else:
            print(f"Login failed: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def test_get_invoices(token):
    """Test GET /api/invoices endpoint"""
    print("\n=== Testing GET /api/invoices ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test basic request
    url = f"{BASE_URL}/api/invoices"
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with parameters
    params = {
        "limit": 5,
        "offset": 0,
        "status": "draft"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\nWith parameters - Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error with parameters: {e}")

def test_get_invoice_detail(token, invoice_id=1):
    """Test GET /api/invoices/<id> endpoint"""
    print(f"\n=== Testing GET /api/invoices/{invoice_id} ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}/api/invoices/{invoice_id}"
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("Invoice API Test Script")
    print("=" * 50)
    
    # Get authentication token
    print("Getting authentication token...")
    token = get_auth_token()
    
    if not token:
        print("Failed to get authentication token. Exiting.")
        sys.exit(1)
    
    print(f"Token obtained: {token[:20]}...")
    
    # Test endpoints
    test_get_invoices(token)
    test_get_invoice_detail(token)
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    main()
