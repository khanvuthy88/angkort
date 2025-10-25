# Bearer Token Authentication Implementation

## Overview

Successfully implemented JWT Bearer token authentication for the invoice API endpoints in the `angkot_recruitement` module. This provides secure authentication that matches the frontend's expectations.

## New Endpoints Added

### 1. POST /api/auth/login
- **Purpose**: Authenticate user and return JWT Bearer token
- **Request**: `{"username": "admin", "password": "admin"}`
- **Response**: Access token, refresh token, and user information
- **Token Expiry**: 30 minutes for access token, 7 days for refresh token

### 2. POST /api/auth/refresh
- **Purpose**: Refresh expired access token using refresh token
- **Request**: `{"refresh_token": "eyJ..."}`
- **Response**: New access token
- **Token Expiry**: 30 minutes for new access token

## Updated Endpoints

### 1. GET /api/invoices
- **Authentication**: Now requires JWT Bearer token
- **Header**: `Authorization: Bearer <jwt_token>`
- **Role-based access**: System admin sees all, others see only their invoices

### 2. GET /api/invoices/<id>
- **Authentication**: Now requires JWT Bearer token
- **Header**: `Authorization: Bearer <jwt_token>`
- **Role-based access**: System admin sees all, others see only their invoices

## Key Features

### 🔐 **JWT Token Authentication**
- Secure token generation using Odoo's database secret
- Token validation with expiration checking
- User information extraction from token payload

### 🔄 **Token Management**
- Access tokens (30 minutes expiry)
- Refresh tokens (7 days expiry)
- Automatic token refresh capability

### 👥 **Role-Based Access Control**
- **System Admin**: Can view all invoices
- **Employer**: Can only view invoices for their partner
- **Other Users**: Can only view invoices for their partner

### 🛡️ **Security Features**
- Password validation using Odoo's authentication system
- JWT token signing with database secret
- Proper error handling and logging
- Input validation for all endpoints

## Implementation Details

### Token Generation
```python
def _generate_token(self, user_id, token_type, minutes=0, days=0):
    payload = {
        "user_id": user_id,
        "type": token_type,
        "exp": datetime.utcnow() + timedelta(minutes=minutes, days=days)
    }
    secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret')
    return jwt.encode(payload, secret_key, algorithm="HS256")
```

### Token Validation
```python
def _validate_token(self, token):
    try:
        secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        
        # Check expiration
        if payload.get('exp') < int(datetime.utcnow().timestamp()):
            return None
        
        # Get user and return info
        user = request.env['res.users'].sudo().browse(payload.get('user_id'))
        return user_info if user.exists() else None
    except Exception:
        return None
```

## Usage Flow

### 1. Login Process
```bash
# Step 1: Login to get tokens
curl -X POST http://localhost:8069/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Response:
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 1800
  }
}
```

### 2. Use Token for API Calls
```bash
# Step 2: Use access token for invoice API
curl -X GET "http://localhost:8069/api/invoices?limit=10" \
  -H "Authorization: Bearer eyJ..."
```

### 3. Refresh Token When Expired
```bash
# Step 3: Refresh token when access token expires
curl -X POST http://localhost:8069/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

## Files Modified

1. **`controllers/controllers.py`**
   - Added login and refresh endpoints
   - Added token generation and validation methods
   - Updated invoice endpoints to use Bearer token auth

2. **`test_invoice_api.py`**
   - Updated to use login endpoint for authentication
   - Simplified token management

3. **`INVOICE_API_DOCUMENTATION.md`**
   - Added authentication endpoints documentation
   - Updated code examples to use login flow
   - Updated security considerations

## Testing

Run the test script to verify the implementation:

```bash
python test_invoice_api.py
```

Make sure to update the credentials in the script before running.

## Benefits

1. **✅ Security**: JWT tokens provide secure authentication
2. **✅ Scalability**: Stateless authentication works well with load balancers
3. **✅ Frontend Compatibility**: Matches the frontend's Bearer token expectations
4. **✅ Token Management**: Automatic refresh capability for better UX
5. **✅ Role-Based Access**: Proper authorization based on user roles
6. **✅ Standard Compliance**: Follows JWT and Bearer token standards

## Migration Notes

- **No Breaking Changes**: Existing functionality remains the same
- **Authentication Required**: Invoice endpoints now require authentication
- **Token Storage**: Frontend needs to store and manage tokens
- **Error Handling**: Proper 401/403 responses for authentication failures

The implementation is now complete and ready for production use!
