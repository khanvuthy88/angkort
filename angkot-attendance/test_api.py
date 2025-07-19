#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HR Attendance API Test Script with JWT Authentication

This script demonstrates how to use the HR Attendance RESTful API
with JWT Bearer token authentication and refresh tokens.

Usage:
    python test_api.py

Requirements:
    - requests library: pip install requests
    - PyJWT library: pip install PyJWT
    - A running Odoo instance with the angkot-attendance module installed
"""

import requests
import json
import sys
import time
from datetime import datetime, date
from typing import Dict, Any, Optional


class AttendanceAPIClient:
    """Client for the HR Attendance API with JWT authentication"""
    
    def __init__(self, base_url: str, username: str = None, password: str = None):
        """
        Initialize the API client
        
        Args:
            base_url: Base URL of the Odoo instance (e.g., http://localhost:8069)
            username: Odoo username for authentication
            password: Odoo password for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None, requires_auth: bool = True) -> Dict[str, Any]:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            requires_auth: Whether the request requires authentication
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.RequestException: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add authentication header if required
        if requires_auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=30
            )
            
            # Handle different response status codes
            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 204:
                return {'message': 'Success (No Content)'}
            elif response.status_code == 400:
                error_data = response.json()
                raise ValueError(f"Bad Request: {error_data.get('error', 'Unknown error')}")
            elif response.status_code == 401:
                # Try to refresh token if we have one
                if self.refresh_token and requires_auth:
                    if self._refresh_access_token():
                        # Retry the request with new token
                        return self._make_request(method, endpoint, data, params, requires_auth)
                raise ValueError("Unauthorized: Invalid or missing token")
            elif response.status_code == 404:
                error_data = response.json()
                raise ValueError(f"Not Found: {error_data.get('error', 'Resource not found')}")
            else:
                error_data = response.json() if response.content else {}
                raise ValueError(f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}")
                
        except requests.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
    
    def login(self) -> Dict[str, Any]:
        """Login and get access/refresh tokens"""
        if not self.username or not self.password:
            raise ValueError("Username and password are required for login")
        
        data = {
            'username': self.username,
            'password': self.password
        }
        
        response = self._make_request('POST', '/api/v1/auth/login', data=data, requires_auth=False)
        
        # Store tokens
        tokens = response.get('tokens', {})
        self.access_token = tokens.get('access_token')
        self.refresh_token = tokens.get('refresh_token')
        
        # Calculate token expiry
        if self.access_token:
            import jwt
            try:
                payload = jwt.decode(self.access_token, options={"verify_signature": False})
                self.token_expires_at = payload.get('exp')
            except:
                pass
        
        return response
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return False
        
        try:
            data = {'refresh_token': self.refresh_token}
            response = self._make_request('POST', '/api/v1/auth/refresh', data=data, requires_auth=False)
            
            # Update tokens
            self.access_token = response.get('access_token')
            
            # Calculate new token expiry
            if self.access_token:
                import jwt
                try:
                    payload = jwt.decode(self.access_token, options={"verify_signature": False})
                    self.token_expires_at = payload.get('exp')
                except:
                    pass
            
            return True
            
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            return False
    
    def logout(self) -> Dict[str, Any]:
        """Logout and revoke refresh token"""
        if not self.refresh_token:
            return {'message': 'No active session'}
        
        data = {'refresh_token': self.refresh_token}
        response = self._make_request('POST', '/api/v1/auth/logout', data=data)
        
        # Clear tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        return response
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get current user information"""
        return self._make_request('GET', '/api/v1/auth/me')
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        return self._make_request('GET', '/api/v1/attendance/health', requires_auth=False)
    
    def create_attendance(self, employee_id: int, check_in: Optional[str] = None, 
                         check_out: Optional[str] = None, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new attendance record
        
        Args:
            employee_id: Employee ID
            check_in: Check-in datetime (ISO format)
            check_out: Check-out datetime (ISO format)
            date_str: Date (YYYY-MM-DD format)
            
        Returns:
            Created attendance record
        """
        data = {'employee_id': employee_id}
        
        if check_in:
            data['check_in'] = check_in
        if check_out:
            data['check_out'] = check_out
        if date_str:
            data['date'] = date_str
        
        return self._make_request('POST', '/api/v1/attendance', data=data)
    
    def list_attendances(self, employee_id: Optional[int] = None, 
                        date_from: Optional[str] = None, date_to: Optional[str] = None,
                        status: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        List attendance records with optional filters
        
        Args:
            employee_id: Filter by employee ID
            date_from: Filter from date (YYYY-MM-DD)
            date_to: Filter to date (YYYY-MM-DD)
            status: Filter by status
            limit: Number of records per page
            offset: Number of records to skip
            
        Returns:
            List of attendance records with pagination info
        """
        params = {'limit': limit, 'offset': offset}
        
        if employee_id:
            params['employee_id'] = employee_id
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        if status:
            params['status'] = status
        
        return self._make_request('GET', '/api/v1/attendance', params=params)
    
    def get_attendance(self, attendance_id: int) -> Dict[str, Any]:
        """
        Get a specific attendance record by ID
        
        Args:
            attendance_id: Attendance record ID
            
        Returns:
            Attendance record
        """
        return self._make_request('GET', f'/api/v1/attendance/{attendance_id}')
    
    def update_attendance(self, attendance_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update an attendance record
        
        Args:
            attendance_id: Attendance record ID
            **kwargs: Fields to update (employee_id, check_in, check_out, etc.)
            
        Returns:
            Updated attendance record
        """
        return self._make_request('PUT', f'/api/v1/attendance/{attendance_id}', data=kwargs)
    
    def delete_attendance(self, attendance_id: int) -> Dict[str, Any]:
        """
        Delete an attendance record
        
        Args:
            attendance_id: Attendance record ID
            
        Returns:
            Success message
        """
        return self._make_request('DELETE', f'/api/v1/attendance/{attendance_id}')
    
    def is_token_expired(self) -> bool:
        """Check if the current access token is expired"""
        if not self.token_expires_at:
            return True
        
        return time.time() > self.token_expires_at


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_response(response: Dict[str, Any], title: str = "Response"):
    """Print a formatted response"""
    print(f"\n{title}:")
    print(json.dumps(response, indent=2, default=str))


def main():
    """Main test function"""
    # Configuration
    BASE_URL = "http://localhost:8069"  # Change this to your Odoo URL
    USERNAME = "admin"  # Change this to your Odoo username
    PASSWORD = "admin"  # Change this to your Odoo password
    
    # Initialize client
    client = AttendanceAPIClient(BASE_URL, USERNAME, PASSWORD)
    
    try:
        # Test 1: Health Check
        print_section("1. Health Check")
        try:
            response = client.health_check()
            print_response(response, "Health Check Response")
        except Exception as e:
            print(f"Health check failed: {e}")
            return
        
        # Test 2: Login
        print_section("2. Login")
        try:
            response = client.login()
            print_response(response, "Login Response")
            print(f"\nAccess Token: {client.access_token[:50]}...")
            print(f"Refresh Token: {client.refresh_token[:50]}...")
        except Exception as e:
            print(f"Login failed: {e}")
            return
        
        # Test 3: Get Current User
        print_section("3. Get Current User")
        try:
            response = client.get_current_user()
            print_response(response, "Current User")
        except Exception as e:
            print(f"Failed to get current user: {e}")
        
        # Test 4: Create Attendance Records
        print_section("4. Create Attendance Records")
        
        # Create attendance with minimal data
        try:
            response = client.create_attendance(employee_id=1)
            print_response(response, "Created Attendance (Minimal)")
            attendance_id = response['id']
        except Exception as e:
            print(f"Failed to create attendance: {e}")
            return
        
        # Create attendance with full data
        try:
            full_attendance = client.create_attendance(
                employee_id=1,
                check_in="2024-01-15T08:30:00",
                check_out="2024-01-15T17:30:00",
                date_str="2024-01-15"
            )
            print_response(full_attendance, "Created Attendance (Full Data)")
        except Exception as e:
            print(f"Failed to create full attendance: {e}")
        
        # Test 5: List Attendances
        print_section("5. List Attendances")
        
        try:
            # List all attendances
            response = client.list_attendances(limit=5)
            print_response(response, "All Attendances (Limited to 5)")
            
            # List attendances for specific employee
            response = client.list_attendances(employee_id=1, limit=3)
            print_response(response, "Attendances for Employee 1")
            
        except Exception as e:
            print(f"Failed to list attendances: {e}")
        
        # Test 6: Get Specific Attendance
        print_section("6. Get Specific Attendance")
        
        try:
            response = client.get_attendance(attendance_id)
            print_response(response, f"Attendance ID {attendance_id}")
        except Exception as e:
            print(f"Failed to get attendance: {e}")
        
        # Test 7: Update Attendance
        print_section("7. Update Attendance")
        
        try:
            response = client.update_attendance(
                attendance_id,
                check_out="2024-01-15T18:00:00"
            )
            print_response(response, f"Updated Attendance ID {attendance_id}")
        except Exception as e:
            print(f"Failed to update attendance: {e}")
        
        # Test 8: Token Refresh Simulation
        print_section("8. Token Refresh Test")
        
        try:
            # Check if token is expired
            if client.is_token_expired():
                print("Token is expired, refreshing...")
                if client._refresh_access_token():
                    print("Token refreshed successfully!")
                else:
                    print("Failed to refresh token")
            else:
                print("Token is still valid")
                print(f"Token expires at: {datetime.fromtimestamp(client.token_expires_at)}")
        except Exception as e:
            print(f"Token refresh test failed: {e}")
        
        # Test 9: List with Date Filters
        print_section("9. List with Date Filters")
        
        try:
            response = client.list_attendances(
                date_from="2024-01-01",
                date_to="2024-01-31",
                limit=10
            )
            print_response(response, "Attendances with Date Filter")
        except Exception as e:
            print(f"Failed to list with date filters: {e}")
        
        # Test 10: Error Handling Examples
        print_section("10. Error Handling Examples")
        
        # Test invalid employee ID
        try:
            response = client.create_attendance(employee_id=99999)
            print_response(response, "Created with Invalid Employee ID")
        except Exception as e:
            print(f"Expected error for invalid employee ID: {e}")
        
        # Test invalid attendance ID
        try:
            response = client.get_attendance(99999)
            print_response(response, "Get Invalid Attendance ID")
        except Exception as e:
            print(f"Expected error for invalid attendance ID: {e}")
        
        # Test 11: Cleanup and Logout
        print_section("11. Cleanup and Logout")
        
        cleanup = input("\nDo you want to delete the test attendance record? (y/N): ").lower().strip()
        if cleanup == 'y':
            try:
                response = client.delete_attendance(attendance_id)
                print_response(response, f"Deleted Attendance ID {attendance_id}")
            except Exception as e:
                print(f"Failed to delete attendance: {e}")
        else:
            print("Skipping cleanup")
        
        # Logout
        try:
            response = client.logout()
            print_response(response, "Logout Response")
        except Exception as e:
            print(f"Logout failed: {e}")
        
        print_section("Test Complete")
        print("All tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("HR Attendance API Test Script with JWT Authentication")
    print("=" * 60)
    print("This script will test all the API endpoints with JWT authentication.")
    print("Make sure your Odoo instance is running and the module is installed.")
    print("Update the BASE_URL, USERNAME, and PASSWORD variables in the script before running.")
    
    # Check if required libraries are available
    try:
        import requests
    except ImportError:
        print("\nError: requests library not found.")
        print("Please install it using: pip install requests")
        sys.exit(1)
    
    try:
        import jwt
    except ImportError:
        print("\nError: PyJWT library not found.")
        print("Please install it using: pip install PyJWT")
        sys.exit(1)
    
    # Ask for confirmation
    confirm = input("\nDo you want to proceed with the tests? (y/N): ").lower().strip()
    if confirm == 'y':
        main()
    else:
        print("Test cancelled.") 