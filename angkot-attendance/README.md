# HR Attendance RESTful API

A complete RESTful API for managing employee attendance records in Odoo, built with Odoo Controllers and following RESTful principles with JWT Bearer token authentication.

## 🚀 Features

- ✅ **Full CRUD Operations**: Create, Read, Update, Delete attendance records
- ✅ **JWT Authentication**: Secure Bearer token authentication with refresh tokens
- ✅ **Input Validation**: Comprehensive validation with custom validators
- ✅ **Error Handling**: Proper HTTP status codes and error messages
- ✅ **Pagination**: Built-in pagination support
- ✅ **Filtering**: Advanced filtering capabilities
- ✅ **Logging**: Comprehensive logging for debugging
- ✅ **Health Check**: API status monitoring endpoint

## 📋 Requirements

- Odoo 18.0 or later
- Python 3.8+
- PostgreSQL database
- `PyJWT` library (for JWT authentication)
- `requests` library (for testing)

## 🛠️ Installation

### 1. Install the Module

1. Copy the `angkot-attendance` module to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the module from the Apps menu

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. JWT Configuration

1. Update the JWT secret key in `controllers.py`:
   ```python
   JWT_SECRET_KEY = "your-super-secret-jwt-key-change-in-production"
   ```

2. Configure token expiry times if needed:
   ```python
   ACCESS_TOKEN_EXPIRY = timedelta(hours=1)  # 1 hour
   REFRESH_TOKEN_EXPIRY = timedelta(days=30)  # 30 days
   ```

### 4. Security Considerations

- ✅ Change the default JWT secret key
- ✅ Use HTTPS in production
- ✅ Implement rate limiting
- ✅ Consider implementing additional security measures
- ✅ Restrict API access to specific IP addresses if needed

## 📚 API Documentation

### Base URL
```
http://your-odoo-domain.com/api/v1/attendance
```

### Authentication
The API uses JWT Bearer token authentication. All protected endpoints require a valid access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | Login and get tokens |
| `POST` | `/auth/refresh` | Refresh access token |
| `GET` | `/auth/me` | Get current user |
| `POST` | `/auth/logout` | Logout and revoke token |
| `GET` | `/health` | Health check |
| `POST` | `/` | Create attendance |
| `GET` | `/` | List attendances |
| `GET` | `/{id}` | Get attendance by ID |
| `PUT` | `/{id}` | Update attendance |
| `DELETE` | `/{id}` | Delete attendance |

### Data Models

#### Attendance Record
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

#### Status Values
- `present`: Employee is currently checked in
- `absent`: No attendance record for the day
- `late`: Employee checked in after 9:00 AM
- `on_time`: Employee checked in on time and worked full day
- `early_departure`: Employee checked out before 5:00 PM

## 🧪 Testing

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

### Using cURL

#### Authentication Flow
```bash
# 1. Login
curl -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# 2. Use access token
ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
curl -X GET http://localhost:8069/api/v1/attendance \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. Refresh token
curl -X POST http://localhost:8069/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}'

# 4. Logout
curl -X POST http://localhost:8069/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}'
```

#### Attendance Operations
```bash
# Create attendance
curl -X POST http://localhost:8069/api/v1/attendance \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"employee_id": 1, "check_in": "2024-01-15T09:00:00"}'

# List attendances
curl -X GET "http://localhost:8069/api/v1/attendance?limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Get attendance by ID
curl -X GET http://localhost:8069/api/v1/attendance/123 \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Update attendance
curl -X PUT http://localhost:8069/api/v1/attendance/123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"check_out": "2024-01-15T18:00:00"}'

# Delete attendance
curl -X DELETE http://localhost:8069/api/v1/attendance/123 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Using Postman

1. Import the provided Postman collection
2. Set the base URL to your Odoo domain
3. Run the Login request to get tokens
4. Tokens will be automatically stored in collection variables
5. Test each endpoint

## 🔍 Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |

### Error Response Format
```json
{
  "error": "Error message description",
  "type": "error_type"
}
```

### Common Error Types

- `validation_error`: Input validation failed
- `authentication_error`: JWT token validation failed
- `unauthorized`: Invalid or missing token
- `not_found`: Resource not found
- `api_error`: Business logic error
- `internal_error`: Unexpected server error

## 🏗️ Architecture

### Code Structure

```
angkot-attendance/
├── controllers/
│   ├── __init__.py
│   └── controllers.py          # Main API controller with JWT auth
├── models/
│   ├── __init__.py
│   └── hr_attendance.py        # Extended hr.attendance model
├── views/
│   ├── views.xml
│   └── templates.xml
├── security/
│   └── ir.model.access.csv
├── __manifest__.py
├── API_DOCUMENTATION.md        # Complete API documentation
├── Attendance_API_Postman_Collection.json
├── test_api.py                 # Python test client with JWT auth
├── requirements.txt
└── README.md
```

### Design Patterns

- **MVC Pattern**: Models, Views, Controllers
- **Service Layer**: Business logic separation
- **Validator Pattern**: Input validation
- **Serializer Pattern**: Data transformation
- **JWT Authentication**: Token-based authentication
- **Error Handling**: Centralized error management

## 🚀 Deployment

### Development
```bash
# Start Odoo with the module
./odoo-bin -d your_database -i angkot-attendance --dev=all
```

### Production
1. Install the module in production Odoo
2. Configure JWT secret key securely
3. Set up HTTPS
4. Implement rate limiting
5. Monitor API usage

## 🔧 Customization

### Adding New Fields

1. Extend the `hr.attendance` model in `models/hr_attendance.py`
2. Update the validator in `controllers.py`
3. Update the serializer
4. Add migration scripts if needed

### Adding New Endpoints

1. Add new route in `AttendanceController`
2. Implement validation logic
3. Add service layer methods
4. Update documentation

## 📊 Monitoring

### Logging
Enable debug logging in Odoo to see detailed API request/response information:
```python
# In Odoo configuration
log_level = debug
```

### Health Check
Monitor API health:
```bash
curl http://your-domain.com/api/v1/attendance/health
```

### Token Management

- Access tokens expire after 1 hour
- Refresh tokens expire after 30 days
- Refresh tokens can be revoked during logout
- Store refresh tokens securely on the client side

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This module is licensed under LGPL-3.0.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the Odoo community forums

## 📈 Roadmap

- [x] JWT authentication
- [ ] Rate limiting
- [ ] API versioning
- [ ] Bulk operations
- [ ] Webhook support
- [ ] Advanced filtering
- [ ] Export functionality
- [ ] Real-time notifications

## 🔗 Related Links

- [Odoo Documentation](https://www.odoo.com/documentation)
- [Odoo API Reference](https://www.odoo.com/documentation/18.0/developer/reference.html)
- [RESTful API Best Practices](https://restfulapi.net/)
- [HTTP Status Codes](https://httpstatuses.com/)
- [JWT.io](https://jwt.io/) 