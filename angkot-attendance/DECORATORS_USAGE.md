# Route Decorators Usage Guide

This document explains how to use the route decorators for authentication and request handling in the Attendance API.

## Available Decorators

### 1. `@require_auth`
**Purpose**: Requires JWT Bearer token authentication for the endpoint.

**Usage**:
```python
@require_auth
@http.route('/api/v1/protected-endpoint', type='http', methods=['GET'], auth='public', csrf=False)
def protected_endpoint(self, **kwargs):
    # This endpoint requires authentication
    # User info is available in request.auth_user
    # Token payload is available in request.auth_payload
    pass
```

**What it does**:
- Extracts Bearer token from Authorization header
- Validates the JWT token
- Stores authenticated user in `request.auth_user`
- Stores token payload in `request.auth_payload`
- Returns 401 error if authentication fails

### 2. `@optional_auth`
**Purpose**: Allows optional authentication - endpoint works with or without authentication.

**Usage**:
```python
@optional_auth
@http.route('/api/v1/public-endpoint', type='http', methods=['GET'], auth='public', csrf=False)
def public_endpoint(self, **kwargs):
    # This endpoint works with or without authentication
    if request.auth_user:
        # User is authenticated
        pass
    else:
        # No authentication provided
        pass
```

**What it does**:
- Tries to authenticate if Authorization header is present
- Doesn't fail if no authentication is provided
- Sets `request.auth_user` to None if no auth or auth fails

### 3. `@require_json`
**Purpose**: Requires JSON request body and parses it automatically.

**Usage**:
```python
@require_json
@http.route('/api/v1/json-endpoint', type='http', methods=['POST'], auth='public', csrf=False)
def json_endpoint(self, **kwargs):
    # JSON data is automatically parsed and available in request.json_data
    data = request.json_data
    pass
```

**What it does**:
- Parses JSON from request body
- Stores parsed data in `request.json_data`
- Returns 400 error if JSON is invalid

### 4. `@require_role(role_name)`
**Purpose**: Requires specific user role/group for access.

**Usage**:
```python
@require_role('hr_attendance.group_hr_attendance_manager')
@http.route('/api/v1/admin-endpoint', type='http', methods=['GET'], auth='public', csrf=False)
def admin_endpoint(self, **kwargs):
    # Only users with hr_attendance_manager role can access this
    pass
```

**What it does**:
- Authenticates the user first
- Checks if user has the specified role/group
- Returns 403 error if user lacks required role

## Combining Decorators

You can combine multiple decorators. The order matters - they are executed from top to bottom:

```python
@require_auth                    # 1. Authenticate user
@require_role('hr.group_hr_user') # 2. Check role
@require_json                    # 3. Parse JSON body
@http.route('/api/v1/endpoint', type='http', methods=['POST'], auth='public', csrf=False)
def endpoint(self, **kwargs):
    # All checks passed, process the request
    data = request.json_data
    user = request.auth_user
    pass
```

## Common Decorator Combinations

### Public Endpoints (No Auth Required)
```python
@http.route('/api/v1/health', type='http', methods=['GET'], auth='public', csrf=False)
def health_check(self, **kwargs):
    # No decorators needed for public endpoints
    pass
```

### Authentication Endpoints
```python
@require_json
@http.route('/api/v1/auth/login', type='http', methods=['POST'], auth='public', csrf=False)
def login(self, **kwargs):
    # Requires JSON body but no authentication
    pass
```

### Protected CRUD Endpoints
```python
@require_auth
@require_json
@http.route('/api/v1/attendance', type='http', methods=['POST'], auth='public', csrf=False)
def create_attendance(self, **kwargs):
    # Requires authentication and JSON body
    pass
```

### Read-Only Protected Endpoints
```python
@require_auth
@http.route('/api/v1/attendance', type='http', methods=['GET'], auth='public', csrf=False)
def list_attendances(self, **kwargs):
    # Requires authentication but no JSON body (uses query params)
    pass
```

### Admin-Only Endpoints
```python
@require_role('hr_attendance.group_hr_attendance_manager')
@http.route('/api/v1/admin/stats', type='http', methods=['GET'], auth='public', csrf=False)
def admin_stats(self, **kwargs):
    # Requires specific role
    pass
```

## Accessing Decorator Data

Inside your endpoint methods, you can access data set by decorators:

```python
@require_auth
@require_json
@http.route('/api/v1/example', type='http', methods=['POST'], auth='public', csrf=False)
def example(self, **kwargs):
    # Access authenticated user
    user = request.auth_user
    user_id = user.id
    employee = user.employee_id
    
    # Access token payload
    payload = request.auth_payload
    token_user_id = payload.get('user_id')
    
    # Access parsed JSON data
    data = request.json_data
    field_value = data.get('field_name')
    
    # Process the request...
    pass
```

## Error Handling

All decorators handle errors automatically and return appropriate HTTP responses:

- **Authentication errors**: 401 Unauthorized
- **Authorization errors**: 403 Forbidden  
- **Validation errors**: 400 Bad Request
- **JSON parsing errors**: 400 Bad Request

## Best Practices

1. **Always use `@require_auth` for sensitive endpoints**
2. **Use `@require_json` for POST/PUT endpoints that expect JSON**
3. **Use `@require_role` for role-based access control**
4. **Use `@optional_auth` for endpoints that can work with or without authentication**
5. **Order decorators logically**: auth → role → json → route
6. **Keep endpoints simple**: let decorators handle common concerns

## Example: Complete Endpoint

```python
@require_auth
@require_role('hr_attendance.group_hr_attendance_officer')
@require_json
@http.route('/api/v1/attendance/bulk-update', type='http', methods=['PUT'], auth='public', csrf=False)
def bulk_update_attendances(self, **kwargs):
    """Bulk update attendance records - requires officer role"""
    try:
        # Data is already validated and parsed by decorators
        data = request.json_data
        user = request.auth_user
        
        # Process the bulk update
        attendance_ids = data.get('attendance_ids', [])
        update_data = data.get('update_data', {})
        
        # Your business logic here...
        
        return Response(
            json.dumps({'message': 'Bulk update completed'}),
            status=200,
            content_type='application/json'
        )
        
    except Exception as e:
        return self._handle_error(e)
```

This approach makes your API endpoints clean, secure, and maintainable by centralizing common concerns in decorators. 