#!/usr/bin/env python3
"""
Test script for the updated Authentication API endpoints.

This script demonstrates how to use the updated login, refresh, and logout methods
that now accept HTTP requests instead of JSON-RPC.

Requirements:
- requests package for HTTP requests
- Valid Odoo user credentials
- Odoo server running on localhost:8069

Usage:
    python test_auth_api.py
"""

import json
import requests
from typing import Dict, Optional


class AuthAPIClient:
    """Client for testing the Authentication API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8069"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def login(self, username: str, password: str) -> Dict:
        """
        Login with username and password.
        
        Args:
            username (str): User's login username/email
            password (str): User's password
            
        Returns:
            Dict: Response from the login endpoint
        """
        url = f"{self.base_url}/api/login"
        data = {
            "username": username,
            "password": password
        }
        
        print(f"🔐 Making login request to: {url}")
        print(f"📤 Request data: {data}")
        print(f"📋 Request headers: {dict(self.session.headers)}")
        
        try:
            response = self.session.post(url, json=data)
            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"📥 Response body: {response_data}")
            except json.JSONDecodeError:
                print(f"📥 Response text (not JSON): {response.text}")
                return {"error": "Invalid JSON response", "text": response.text}
            
            if response.status_code == 200 and response_data.get('status'):
                # Store tokens for future use
                self.access_token = response_data['data']['access_token']
                self.refresh_token = response_data['data']['refresh_token']
                
                # Update session headers with access token
                self.session.headers.update({
                    'Authorization': f"Bearer {self.access_token}"
                })
                
                print("✅ Login successful!")
                print(f"   User: {response_data['data']['username']}")
                print(f"   Access Token: {self.access_token[:20]}...")
                print(f"   Refresh Token: {self.refresh_token[:20]}...")
                
            else:
                print("❌ Login failed!")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response_data}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Login request error: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return {"error": str(e)}
    
    def refresh_token(self) -> Dict:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            Dict: Response from the refresh endpoint
        """
        if not self.refresh_token:
            print("❌ No refresh token available. Please login first.")
            return {"error": "No refresh token available"}
        
        url = f"{self.base_url}/api/refresh"
        data = {
            "refresh_token": self.refresh_token
        }
        
        print(f"🔄 Making refresh request to: {url}")
        print(f"📤 Request data: {data}")
        
        try:
            response = self.session.post(url, json=data)
            print(f"📥 Response status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"📥 Response body: {response_data}")
            except json.JSONDecodeError:
                print(f"📥 Response text (not JSON): {response.text}")
                return {"error": "Invalid JSON response", "text": response.text}
            
            if response.status_code == 200 and response_data.get('status'):
                # Update access token
                self.access_token = response_data['data']['access_token']
                
                # Update session headers
                self.session.headers.update({
                    'Authorization': f"Bearer {self.access_token}"
                })
                
                print("✅ Token refreshed successfully!")
                print(f"   New Access Token: {self.access_token[:20]}...")
                
            else:
                print("❌ Token refresh failed!")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response_data}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Refresh request error: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            print(f"❌ Token refresh error: {str(e)}")
            return {"error": str(e)}
    
    def logout(self) -> Dict:
        """
        Logout and invalidate the current access token.
        
        Returns:
            Dict: Response from the logout endpoint
        """
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return {"error": "No access token available"}
        
        url = f"{self.base_url}/api/logout"
        
        print(f"🚪 Making logout request to: {url}")
        print(f"📋 Request headers: {dict(self.session.headers)}")
        
        try:
            response = self.session.post(url)
            print(f"📥 Response status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"📥 Response body: {response_data}")
            except json.JSONDecodeError:
                print(f"📥 Response text (not JSON): {response.text}")
                return {"error": "Invalid JSON response", "text": response.text}
            
            if response.status_code == 200 and response_data.get('status'):
                print("✅ Logout successful!")
                
                # Clear tokens
                self.access_token = None
                self.refresh_token = None
                
                # Remove authorization header
                if 'Authorization' in self.session.headers:
                    del self.session.headers['Authorization']
                
            else:
                print("❌ Logout failed!")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response_data}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Logout request error: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            print(f"❌ Logout error: {str(e)}")
            return {"error": str(e)}
    
    def test_protected_endpoint(self) -> Dict:
        """
        Test a protected endpoint to verify the access token works.
        
        Returns:
            Dict: Response from the test endpoint
        """
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return {"error": "No access token available"}
        
        url = f"{self.base_url}/api/test"
        
        print(f"🧪 Making test request to: {url}")
        print(f"📋 Request headers: {dict(self.session.headers)}")
        
        try:
            response = self.session.post(url, json={"test": "data"})
            print(f"📥 Response status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"📥 Response body: {response_data}")
            except json.JSONDecodeError:
                print(f"📥 Response text (not JSON): {response.text}")
                return {"error": "Invalid JSON response", "text": response.text}
            
            if response.status_code == 200:
                print("✅ Protected endpoint test successful!")
                print(f"   Response: {response_data}")
            else:
                print("❌ Protected endpoint test failed!")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response_data}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Test request error: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            print(f"❌ Protected endpoint test error: {str(e)}")
            return {"error": str(e)}


def main():
    """Main test function."""
    print("🚀 Testing Authentication API Endpoints")
    print("=" * 50)
    
    # Initialize client
    client = AuthAPIClient()
    
    # Test credentials (replace with actual credentials)
    username = "admin"  # Replace with actual username
    password = "admin"  # Replace with actual password
    
    print(f"\n📝 Testing with username: {username}")
    print(f"🌐 Base URL: {client.base_url}")
    
    # Test 1: Login
    print("\n1️⃣ Testing Login...")
    login_result = client.login(username, password)
    
    if not login_result.get('status'):
        print("❌ Cannot proceed without successful login")
        print("💡 Check your credentials and make sure the Odoo server is running")
        return
    
    # Test 2: Test protected endpoint
    print("\n2️⃣ Testing Protected Endpoint...")
    client.test_protected_endpoint()
    
    # Test 3: Refresh token
    print("\n3️⃣ Testing Token Refresh...")
    client.refresh_token()
    
    # Test 4: Test protected endpoint again with new token
    print("\n4️⃣ Testing Protected Endpoint with Refreshed Token...")
    client.test_protected_endpoint()
    
    # Test 5: Logout
    print("\n5️⃣ Testing Logout...")
    client.logout()
    
    # Test 6: Try to access protected endpoint after logout
    print("\n6️⃣ Testing Protected Endpoint After Logout...")
    client.test_protected_endpoint()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()
