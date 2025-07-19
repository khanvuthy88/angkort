# Refresh Token Implementation for Angkort API

## Overview

This document describes the complete refresh token implementation for the Angkort API, providing secure authentication with automatic token renewal capabilities.

## Authentication Flow

### 1. Login Process
```
User Login → Validate Credentials → Generate Access + Refresh Tokens → Store in Database → Return Tokens
```

### 2. Token Usage
```
API Request → Validate Access Token → Process Request → Return Response
```

### 3. Token Refresh Process
```
Access Token Expired → Use Refresh Token → Generate New Access Token → Continue API Usage
```

## Token Types

### Access Token
- **Purpose**: Short-lived token for API authentication
- **Lifetime**: 30 minutes
- **Usage**: Required in Authorization header for protected endpoints
- **Format**: `Bearer <access_token>`

### Refresh Token
- **Purpose**: Long-lived token for generating new access tokens
- **Lifetime**: 7 days
- **Usage**: Used to obtain new access tokens when current one expires
- **Storage**: Should be stored securely by the client

## API Endpoints

### 1. Login
**POST** `/angkort/api/v1/login`

**Request Body:**
```json
{
    "username": "admin",
    "password": "password123"
}
```

**Response:**
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
        "username": "admin"
    }
}
```

### 2. Refresh Token
**POST** `/angkort/api/v1/refresh`

**Request Body:**
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
    "status": true,
    "message": "Token refreshed successfully",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "Bearer",
        "expires_in": 1800,
        "user_id": 1,
        "username": "admin"
    }
}
```

### 3. Validate Token
**POST** `/angkort/api/v1/validate`

**Request Body:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
    "status": true,
    "message": "Token is valid",
    "data": {
        "user_id": 1,
        "username": "admin",
        "expires_in": 1200
    }
}
```

### 4. Logout
**POST** `/angkort/api/v1/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "status": true,
    "message": "Logout successful"
}
```

### 5. Revoke All Tokens
**POST** `/angkort/api/v1/revoke-all`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "status": true,
    "message": "All tokens revoked successfully",
    "data": {
        "revoked_count": 3
    }
}
```

## Security Features

### 1. Token Hashing
- All tokens are hashed using SHA256 before storage in the database
- Prevents token exposure in database logs
- Enhances security against database breaches

### 2. Token Expiration
- Access tokens expire after 30 minutes
- Refresh tokens expire after 7 days
- Automatic cleanup of expired tokens

### 3. Token Validation
- Server-side validation of token authenticity
- Database lookup for active tokens
- Expiration time verification

### 4. Secure Logout
- Tokens are properly invalidated on logout
- Deactivation timestamp recorded
- Prevents token reuse after logout

## Database Schema

### res.user.token Model
```python
class ResUserToken(models.Model):
    _name = "res.user.token"
    
    user_id = fields.Many2one('res.users', required=True)
    access_token = fields.Char(required=True)  # Hashed
    refresh_token = fields.Char(required=True)  # Hashed
    expires_at = fields.Datetime()  # Access token expiry
    refresh_expires_at = fields.Datetime()  # Refresh token expiry
    active = fields.Boolean(default=True)
    deactivated_at = fields.Datetime()
```

## Client Implementation Guide

### 1. Token Storage
```javascript
// Store tokens securely
localStorage.setItem('access_token', response.data.access_token);
localStorage.setItem('refresh_token', response.data.refresh_token);
localStorage.setItem('token_expiry', Date.now() + (response.data.expires_in * 1000));
```

### 2. Automatic Token Refresh
```javascript
// Check if token needs refresh
function isTokenExpired() {
    const expiry = localStorage.getItem('token_expiry');
    return Date.now() > parseInt(expiry);
}

// Refresh token function
async function refreshAccessToken() {
    const refresh_token = localStorage.getItem('refresh_token');
    
    try {
        const response = await fetch('/angkort/api/v1/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token })
        });
        
        const data = await response.json();
        
        if (data.status) {
            localStorage.setItem('access_token', data.data.access_token);
            localStorage.setItem('token_expiry', Date.now() + (data.data.expires_in * 1000));
            return data.data.access_token;
        } else {
            // Refresh token expired, redirect to login
            localStorage.clear();
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        localStorage.clear();
        window.location.href = '/login';
    }
}
```

### 3. API Request Interceptor
```javascript
// Axios interceptor for automatic token refresh
axios.interceptors.request.use(async (config) => {
    if (isTokenExpired()) {
        const newToken = await refreshAccessToken();
        config.headers.Authorization = `Bearer ${newToken}`;
    } else {
        const token = localStorage.getItem('access_token');
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

axios.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response.status === 401) {
            // Try to refresh token
            try {
                const newToken = await refreshAccessToken();
                error.config.headers.Authorization = `Bearer ${newToken}`;
                return axios.request(error.config);
            } catch (refreshError) {
                // Refresh failed, redirect to login
                localStorage.clear();
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
    "status": false,
    "message": "Missing required field",
    "error": "refresh_token is required"
}
```

#### 401 Unauthorized
```json
{
    "status": false,
    "message": "Invalid refresh token",
    "error": "Refresh token is expired or invalid"
}
```

#### 500 Internal Server Error
```json
{
    "status": false,
    "message": "Error refreshing token",
    "error": "Database connection failed"
}
```

## Best Practices

### 1. Client-Side
- Store refresh tokens securely (httpOnly cookies recommended)
- Implement automatic token refresh before expiration
- Handle token refresh failures gracefully
- Clear all tokens on logout

### 2. Server-Side
- Use HTTPS in production
- Implement rate limiting for token endpoints
- Log security events (failed logins, token revocations)
- Regular cleanup of expired tokens

### 3. Security
- Never expose refresh tokens in client-side code
- Implement token rotation for sensitive operations
- Monitor for suspicious token usage patterns
- Regular security audits

## Testing

### Test Cases

1. **Successful Login**
   - Valid credentials should return both tokens
   - Verify token expiration times

2. **Token Refresh**
   - Valid refresh token should return new access token
   - Invalid refresh token should return 401

3. **Token Validation**
   - Valid access token should return user info
   - Expired token should return 401

4. **Logout**
   - Should invalidate current access token
   - Should not affect other user sessions

5. **Revoke All Tokens**
   - Should invalidate all user tokens
   - Should return count of revoked tokens

## Migration Guide

### From Old Authentication System

1. **Update Login Response**
   - Old: Returns only `token_key`
   - New: Returns `access_token` and `refresh_token`

2. **Update Client Code**
   - Implement token refresh logic
   - Update API request headers
   - Handle token expiration

3. **Database Migration**
   - Ensure `res.user.token` model is installed
   - Migrate existing tokens if necessary

## Troubleshooting

### Common Issues

1. **Token Not Found**
   - Check if token is properly hashed
   - Verify token is stored in database
   - Check token expiration

2. **Refresh Token Expired**
   - User must login again
   - Clear client-side storage
   - Redirect to login page

3. **Database Connection Issues**
   - Check Odoo database connectivity
   - Verify model permissions
   - Check server logs

## Future Enhancements

1. **Token Rotation**
   - Implement refresh token rotation
   - Enhanced security for long-lived sessions

2. **Multi-Device Support**
   - Track device information
   - Allow selective token revocation

3. **Audit Logging**
   - Log all authentication events
   - Monitor for suspicious activity

4. **Rate Limiting**
   - Implement rate limiting for token endpoints
   - Prevent brute force attacks 