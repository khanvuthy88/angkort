# HR Attendance RESTful API Documentation

## Overview

This RESTful API provides full CRUD operations for managing employee attendance records in Odoo. The API is built using Odoo Controllers and follows RESTful principles with proper validation, error handling, and JWT Bearer token authentication.

## Features

- ✅ **Full CRUD Operations**: Create, Read, Update, Delete attendance records
- ✅ **JWT Authentication**: Secure Bearer token authentication with refresh tokens
- ✅ **Input Validation**: Comprehensive validation with custom validators
- ✅ **Error Handling**: Proper HTTP status codes and error messages
- ✅ **Pagination**: Built-in pagination support
- ✅ **Filtering**: Advanced filtering capabilities
- ✅ **Logging**: Comprehensive logging for debugging
- ✅ **Health Check**: API status monitoring endpoint

## API Endpoints

### Base URL
```
http://your-odoo-domain.com/api/v1/attendance
```

### Authentication
The API uses JWT Bearer token authentication. All protected endpoints require a valid access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Authentication Endpoints

#### 1. Login
**POST** `/api/v1/auth/login`

Authenticate user and get access/refresh tokens.

**Request Body:**
```json
{
    "username": "admin",
    "password": "admin"
}
```

**Response (200 OK):**
```json
{
    "user": {
        "user_id": 1,
        "username": "admin",
        "name": "Administrator",
        "employee_id": 1,
        "employee_name": "John Doe",
        "email": "admin@example.com",
        "groups": ["Administration", "Human Resources"]
    },
    "tokens": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "Bearer",
        "expires_in": 3600
    }
}
```

#### 2. Refresh Token
**POST** `/api/v1/auth/refresh`

Refresh access token using refresh token.

**Request Body:**
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

#### 3. Get Current User
**GET** `/api/v1/auth/me`

Get current user information using access token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
    "user_id": 1,
    "username": "admin",
    "name": "Administrator",
    "employee_id": 1,
    "employee_name": "John Doe",
    "email": "admin@example.com",
    "groups": ["Administration", "Human Resources"]
}
```

#### 4. Logout
**POST** `/api/v1/auth/logout`

Logout and revoke refresh token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
    "message": "Successfully logged out"
}
```

### Attendance Endpoints

#### 1. Create Attendance Record
**POST** `/api/v1/attendance`

Creates a new attendance record.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "employee_id": 1,
    "check_in": "2024-01-15T09:00:00",
    "check_out": "2024-01-15T17:00:00",
    "date": "2024-01-15",
    "status": "present"
}
```

**Response (201 Created):**
```json
{
    "id": 123,
    "employee_id": 1,
    "employee_name": "John Doe",
    "check_in": "2024-01-15T09:00:00",
    "check_out": "2024-01-15T17:00:00",
    "date": "2024-01-15",
    "worked_hours": 8.0,
    "status": "on_time",
    "department_id": 1,
    "department_name": "IT Department",
    "created_at": "2024-01-15T09:00:00",
    "updated_at": "2024-01-15T09:00:00"
}
```

#### 2. List Attendance Records
**GET** `/api/v1/attendance`

Retrieves a list of attendance records with optional filtering and pagination.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `employee_id` (optional): Filter by employee ID
- `date_from` (optional): Filter from date (YYYY-MM-DD)
- `date_to` (optional): Filter to date (YYYY-MM-DD)
- `status` (optional): Filter by status
- `limit` (optional): Number of records per page (default: 50)
- `offset` (optional): Number of records to skip (default: 0)

**Example Request:**
```
GET /api/v1/attendance?employee_id=1&date_from=2024-01-01&date_to=2024-01-31&limit=10&offset=0
```

**Response (200 OK):**
```json
{
    "attendances": [
        {
            "id": 123,
            "employee_id": 1,
            "employee_name": "John Doe",
            "check_in": "2024-01-15T09:00:00",
            "check_out": "2024-01-15T17:00:00",
            "date": "2024-01-15",
            "worked_hours": 8.0,
            "status": "on_time",
            "department_id": 1,
            "department_name": "IT Department",
            "created_at": "2024-01-15T09:00:00",
            "updated_at": "2024-01-15T09:00:00"
        }
    ],
    "total_count": 1,
    "limit": 10,
    "offset": 0
}
```

#### 3. Get Attendance Record by ID
**GET** `/api/v1/attendance/{id}`

Retrieves a specific attendance record by ID.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Example Request:**
```
GET /api/v1/attendance/123
```

**Response (200 OK):**
```json
{
    "id": 123,
    "employee_id": 1,
    "employee_name": "John Doe",
    "check_in": "2024-01-15T09:00:00",
    "check_out": "2024-01-15T17:00:00",
    "date": "2024-01-15",
    "worked_hours": 8.0,
    "status": "on_time",
    "department_id": 1,
    "department_name": "IT Department",
    "created_at": "2024-01-15T09:00:00",
    "updated_at": "2024-01-15T09:00:00"
}
```

#### 4. Update Attendance Record
**PUT** `/api/v1/attendance/{id}`

Updates an existing attendance record.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "check_out": "2024-01-15T18:00:00",
    "status": "late"
}
```

**Response (200 OK):**
```json
{
    "id": 123,
    "employee_id": 1,
    "employee_name": "John Doe",
    "check_in": "2024-01-15T09:00:00",
    "check_out": "2024-01-15T18:00:00",
    "date": "2024-01-15",
    "worked_hours": 9.0,
    "status": "late",
    "department_id": 1,
    "department_name": "IT Department",
    "created_at": "2024-01-15T09:00:00",
    "updated_at": "2024-01-15T18:00:00"
}
```

#### 5. Delete Attendance Record
**DELETE** `/api/v1/attendance/{id}`

Deletes an attendance record.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Example Request:**
```
DELETE /api/v1/attendance/123
```

**Response (204 No Content):**
```json
{
    "message": "Attendance record 123 deleted successfully"
}
```

#### 6. Health Check
**GET** `/api/v1/attendance/health`

Health check endpoint to verify API status.

**Response (200 OK):**
```json
{
    "status": "healthy",
    "message": "Attendance API is running"
}
```

## Data Models

### Attendance Record Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | Integer | Primary key, auto-incremented | Auto |
| `employee_id` | Integer | Foreign key referencing employee | Yes |
| `check_in` | DateTime | Timestamp of employee check-in | No (defaults to now) |
| `check_out` | DateTime | Timestamp of employee check-out | No |
| `date` | Date | Date of the attendance record | No (derived from check_in) |
| `worked_hours` | Float | Calculated worked hours | Auto |
| `status` | String | Attendance status | Auto (calculated) |

### Status Values

- `present`: Employee is currently checked in
- `absent`: No attendance record for the day
- `late`: Employee checked in after 9:00 AM
- `on_time`: Employee checked in on time and worked full day
- `early_departure`: Employee checked out before 5:00 PM

### JWT Token Information

#### Access Token
- **Expiry**: 1 hour
- **Usage**: Required for all protected endpoints
- **Header**: `Authorization: Bearer <access_token>`

#### Refresh Token
- **Expiry**: 30 days
- **Usage**: Used to get new access tokens
- **Storage**: Stored securely in database for revocation

## Error Handling

The API returns appropriate HTTP status codes and error messages:

### Error Response Format
```json
{
    "error": "Error message description",
    "type": "error_type"
}
```

### HTTP Status Codes

| Code | Description | Error Type |
|------|-------------|------------|
| 200 | OK | - |
| 201 | Created | - |
| 204 | No Content | - |
| 400 | Bad Request | `validation_error` |
| 401 | Unauthorized | `authentication_error`, `unauthorized` |
| 404 | Not Found | `not_found` |
| 500 | Internal Server Error | `api_error`, `internal_error` |

### Common Error Types

- `validation_error`: Input validation failed
- `authentication_error`: JWT token validation failed
- `unauthorized`: Invalid or missing token
- `not_found`: Resource not found
- `api_error`: Business logic error
- `internal_error`: Unexpected server error

## Example cURL Commands

### Authentication Flow

#### 1. Login
```bash
curl -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
  }'
```

#### 2. Use Access Token
```bash
# Store the access token from login response
ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Use the token for API calls
curl -X GET http://localhost:8069/api/v1/attendance \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### 3. Refresh Token
```bash
curl -X POST http://localhost:8069/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

#### 4. Logout
```bash
curl -X POST http://localhost:8069/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

### Attendance Operations

#### Create Attendance
```bash
curl -X POST http://localhost:8069/api/v1/attendance \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "employee_id": 1,
    "check_in": "2024-01-15T09:00:00",
    "check_out": "2024-01-15T17:00:00"
  }'
```

#### List Attendances
```bash
curl -X GET "http://localhost:8069/api/v1/attendance?employee_id=1&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Get Attendance by ID
```bash
curl -X GET http://localhost:8069/api/v1/attendance/123 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Update Attendance
```bash
curl -X PUT http://localhost:8069/api/v1/attendance/123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "check_out": "2024-01-15T18:00:00"
  }'
```

#### Delete Attendance
```bash
curl -X DELETE http://localhost:8069/api/v1/attendance/123 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Health Check
```bash
curl -X GET http://localhost:8069/api/v1/attendance/health
```

## Setup and Installation

### 1. Prerequisites
- Odoo 18.0 or later
- Python 3.8+
- PostgreSQL database

### 2. Module Installation
1. Copy the `angkot-attendance` module to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the module from the Apps menu

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. JWT Configuration
1. Update the JWT secret key in `controllers.py`:
   ```python
   JWT_SECRET_KEY = "your-super-secret-jwt-key-change-in-production"
   ```

2. Configure token expiry times if needed:
   ```python
   ACCESS_TOKEN_EXPIRY = timedelta(hours=1)  # 1 hour
   REFRESH_TOKEN_EXPIRY = timedelta(days=30)  # 30 days
   ```

### 5. Security Considerations
- Change the default JWT secret key
- Use HTTPS in production
- Implement rate limiting
- Consider implementing additional security measures
- Restrict API access to specific IP addresses if needed

## Testing

### Using the Test Script
1. Update the configuration in `test_api.py`:
   ```python
   BASE_URL = "http://localhost:8069"  # Your Odoo URL
   USERNAME = "admin"  # Your Odoo username
   PASSWORD = "admin"  # Your Odoo password
   ```

2. Run the test script:
   ```bash
   python test_api.py
   ```

### Using Postman
1. Import the provided Postman collection
2. Set the base URL to your Odoo domain
3. Run the Login request to get tokens
4. Tokens will be automatically stored in collection variables
5. Test each endpoint

### Using Python Requests
```python
import requests
import json

base_url = "http://localhost:8069"

# Login
login_data = {
    "username": "admin",
    "password": "admin"
}
response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data)
tokens = response.json()['tokens']
access_token = tokens['access_token']

# Use access token
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Create attendance
data = {
    "employee_id": 1,
    "check_in": "2024-01-15T09:00:00"
}
response = requests.post(f"{base_url}/api/v1/attendance", headers=headers, json=data)
print(response.json())

# List attendances
response = requests.get(f"{base_url}/api/v1/attendance?limit=10", headers=headers)
print(response.json())
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check if the access token is valid and not expired
2. **Token Expired**: Use the refresh token to get a new access token
3. **400 Bad Request**: Verify the request body format and required fields
4. **404 Not Found**: Ensure the attendance record ID exists
5. **500 Internal Server Error**: Check Odoo logs for detailed error information

### Token Management

- Access tokens expire after 1 hour
- Refresh tokens expire after 30 days
- Refresh tokens can be revoked during logout
- Store refresh tokens securely on the client side

### Logging
Enable debug logging in Odoo to see detailed API request/response information:
```python
# In Odoo configuration
log_level = debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This module is licensed under LGPL-3.0.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the Odoo community forums 