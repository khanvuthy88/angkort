# Authentication API Documentation

## Overview

The Authentication API has been updated to accept HTTP requests instead of JSON-RPC, providing proper HTTP status codes and JSON responses. This makes it more compatible with standard REST API practices and easier to integrate with various HTTP clients.

## Base URL

```
http://localhost:8069/angkort/api/v1
```

## Endpoints

### 1. Login

**Endpoint:** `POST /angkort/api/v1/login`

**Description:** Authenticate user and generate access/refresh tokens.

**Authentication:** None (public endpoint)

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
    "username": "admin",
    "password": "password123"
}
```

**Success Response (200):**
```json
{
    "status": true,
    "message": "Login successful",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "Bearer",
        "expires_in": 1800,
        "user_id": 1,
        "username": "admin",
        "name": "Administrator",
        "email": "admin@example.com"
    }
}
```

**Error Responses:**

**400 Bad Request - Invalid JSON:**
```json
{
    "status": false,
    "message": "Invalid JSON format",
    "error": "Expecting property name enclosed in double quotes"
}
```

**400 Bad Request - Missing Fields:**
```json
{
    "status": false,
    "message": "Missing required fields",
    "error": "Username and password are required"
}
```

**401 Unauthorized - Invalid Credentials:**
```json
{
    "status": false,
    "message": "Authentication failed",
    "error": "Invalid username or password"
}
```

**500 Internal Server Error:**
```json
{
    "status": false,
    "message": "Internal server error",
    "error": "An unexpected error occurred during login"
}
```

### 2. Refresh Token

**Endpoint:** `POST /angkort/api/v1/refresh`

**Description:** Generate a new access token using a valid refresh token.

**Authentication:** None (public endpoint)

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
    "status": true,
    "message": "Token refreshed successfully",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "Bearer",
        "expires_in": 1800
    }
}
```

**Error Responses:**

**400 Bad Request - Missing Refresh Token:**
```json
{
    "status": false,
    "message": "Missing required field",
    "error": "Refresh token is required"
}
```

**401 Unauthorized - Invalid Refresh Token:**
```json
{
    "status": false,
    "message": "Authentication failed",
    "error": "Invalid or expired refresh token"
}
```

### 3. Logout

**Endpoint:** `POST /angkort/api/v1/logout`

**Description:** Logout user and invalidate access token.

**Authentication:** Required (Bearer token)

**Request Headers:**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Request Body:** None

**Success Response (200):**
```json
{
    "status": true,
    "message": "Successfully logged out"
}
```

**Error Responses:**

**400 Bad Request - Missing Token:**
```json
{
    "status": false,
    "message": "Access token missing",
    "error": "Authorization header is required"
}
```

**401 Unauthorized - Invalid Token:**
```json
{
    "status": false,
    "message": "Authentication failed",
    "error": "Invalid access token"
}
```

## Usage Examples

### Using Python requests

```python
import requests
import json

# Base URL
base_url = "http://localhost:8069/angkort/api/v1"

# Login
login_data = {
    "username": "admin",
    "password": "password123"
}

response = requests.post(f"{base_url}/login", json=login_data)
if response.status_code == 200:
    data = response.json()
    access_token = data['data']['access_token']
    refresh_token = data['data']['refresh_token']
    
    # Use access token for authenticated requests
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Make authenticated request
    auth_response = requests.post(f"{base_url}/test", headers=headers, json={"test": "data"})
    print(auth_response.json())
```

### Using JavaScript/Fetch

```javascript
// Login
async function login(username, password) {
    const response = await fetch('/angkort/api/v1/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });
    
    const data = await response.json();
    
    if (data.status) {
        // Store tokens
        localStorage.setItem('access_token', data.data.access_token);
        localStorage.setItem('refresh_token', data.data.refresh_token);
        return data.data;
    } else {
        throw new Error(data.error);
    }
}

// Make authenticated request
async function makeAuthenticatedRequest(url, data) {
    const access_token = localStorage.getItem('access_token');
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${access_token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    
    return response.json();
}

// Refresh token
async function refreshToken() {
    const refresh_token = localStorage.getItem('refresh_token');
    
    const response = await fetch('/angkort/api/v1/refresh', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh_token })
    });
    
    const data = await response.json();
    
    if (data.status) {
        localStorage.setItem('access_token', data.data.access_token);
        return data.data.access_token;
    } else {
        // Redirect to login
        localStorage.clear();
        window.location.href = '/login';
    }
}
```

### Using cURL

```bash
# Login
curl -X POST http://localhost:8069/angkort/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# Use access token
curl -X POST http://localhost:8069/angkort/api/v1/test \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Refresh token
curl -X POST http://localhost:8069/angkort/api/v1/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'

# Logout
curl -X POST http://localhost:8069/angkort/api/v1/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing

A test script `test_auth_api.py` is provided to test all endpoints:

```bash
python test_auth_api.py
```

Make sure to:
1. Update the credentials in the test script
2. Have the Odoo server running
3. Install required dependencies (`requests`)

## Error Handling

The API now provides consistent error responses with:
- Proper HTTP status codes
- Structured JSON error messages
- Detailed error descriptions
- Consistent response format

## Security Features

- JWT-based authentication
- Access tokens expire in 30 minutes
- Refresh tokens expire in 7 days
- Tokens are stored securely in the database
- CSRF protection disabled for API endpoints
- CORS enabled for cross-origin requests

## Migration Notes

If you were using the previous JSON-RPC endpoints:

1. **Change request type:** From `type='json'` to `type='http'`
2. **Update response handling:** Check HTTP status codes
3. **Update error handling:** Parse error responses from JSON body
4. **Update authentication:** Use `Authorization: Bearer <token>` header

## Dependencies

- Odoo 18+
- `res.user.token` model (custom model for token storage)
- JWT library for token generation
- Standard Odoo HTTP controllers
