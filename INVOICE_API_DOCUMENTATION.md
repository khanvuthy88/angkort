# Invoice API Documentation

## Overview

This document describes the invoice API endpoints implemented in the `angkot_recruitement` module. These endpoints provide role-based access to invoice data with proper authentication and authorization.

## Authentication Endpoints

### 1. POST /angkort/api/v1/login

Authenticate user and get JWT Bearer token.

#### Request Body
```json
{
    "username": "admin",
    "password": "admin"
}
```

#### Response (200 OK)
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
        "email": "admin@example.com",
        "is_merchant": false,
        "is_admin": true
    }
}
```

### 2. POST /angkort/api/v1/refresh

Refresh access token using refresh token.

#### Request Body
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response (200 OK)
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

### 3. POST /angkort/api/v1/logout

Logout user and invalidate access token.

#### Request Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
    "status": true,
    "message": "Successfully logged out"
}
```

## Invoice Endpoints

### 1. GET /api/invoices

Retrieve a paginated list of invoices with role-based access control.

#### Authentication
- **Required**: Bearer token in Authorization header
- **Format**: `Authorization: Bearer <token>`
- **Auth Method**: Uses Odoo's built-in `angkit` authentication method
- **Login Endpoint**: `POST /angkort/api/v1/login`
- **Refresh Endpoint**: `POST /angkort/api/v1/refresh`
- **Logout Endpoint**: `POST /angkort/api/v1/logout`

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Number of invoices per page |
| `offset` | integer | 0 | Number of invoices to skip |
| `status` | string | - | Filter by invoice status (draft, sent, paid, overdue, cancelled) |
| `year` | string | - | Filter by year (YYYY format) |
| `month` | string | - | Filter by month (MM format, requires year) |
| `partner_id` | integer | - | Filter by partner ID |

#### Role-Based Access Control

**System Admin** (`base.group_system` or `base.group_erp_manager`):
- Can view all invoices in the system
- No restrictions on data access

**Employer** (`angkot_recruitement.group_hr_recruitment_employer` or company partner):
- Can only view invoices associated with their partner
- Filtered by `partner_id = user.partner_id.id`

**Other Users**:
- Can only view invoices associated with their partner
- Same restrictions as employers

#### Response Format

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "invoice_number": "INV/2024/0001",
      "user_id": 1,
      "company_name": "Company Name",
      "billing_address": "123 Main St",
      "billing_email": "billing@company.com",
      "billing_phone": "+1-555-0123",
      "issue_date": "2024-01-15T00:00:00",
      "due_date": "2024-02-14T00:00:00",
      "status": "paid",
      "subtotal": 299.00,
      "tax_amount": 23.92,
      "total_amount": 322.92,
      "currency": "USD",
      "payment_method": "Credit Card",
      "payment_date": "2024-01-16T10:30:00",
      "notes": "Payment for Premium Job Posting Package",
      "created_at": "2024-01-15T09:00:00",
      "updated_at": "2024-01-16T10:30:00",
      "line_items": [
        {
          "id": 1,
          "description": "Premium Job Posting Package",
          "quantity": 1,
          "unit_price": 299.00,
          "total_price": 299.00,
          "job_id": 1,
          "job_title": "Senior Software Engineer",
          "package_type": "premium"
        }
      ]
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0,
  "user_role": "system_admin"
}
```

#### Status Mapping

| Odoo State | Odoo Payment State | API Status | Description |
|------------|-------------------|------------|-------------|
| draft | - | draft | Invoice is in draft state |
| posted | not_paid | sent | Invoice is posted but not paid |
| posted | paid | paid | Invoice is fully paid |
| posted | not_paid + overdue | overdue | Invoice is posted, not paid, and past due date |
| cancel | - | cancelled | Invoice is cancelled |

### 2. GET /api/invoices/<invoice_id>

Retrieve detailed information for a specific invoice.

#### Authentication
- **Required**: Bearer token in Authorization header
- **Format**: `Authorization: Bearer <token>`
- **Auth Method**: Uses Odoo's built-in `angkit` authentication method
- **Login Endpoint**: `POST /angkort/api/v1/login`
- **Refresh Endpoint**: `POST /angkort/api/v1/refresh`
- **Logout Endpoint**: `POST /angkort/api/v1/logout`

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | integer | Yes | ID of the invoice to retrieve |

#### Role-Based Access Control

Same access control as the list endpoint:
- **System Admin**: Can view any invoice
- **Employer/Users**: Can only view invoices associated with their partner

#### Response Format

```json
{
  "success": true,
  "data": {
    "id": 1,
    "invoice_number": "INV/2024/0001",
    "user_id": 1,
    "company_name": "Company Name",
    "billing_address": "123 Main St",
    "billing_email": "billing@company.com",
    "billing_phone": "+1-555-0123",
    "issue_date": "2024-01-15T00:00:00",
    "due_date": "2024-02-14T00:00:00",
    "status": "paid",
    "subtotal": 299.00,
    "tax_amount": 23.92,
    "total_amount": 322.92,
    "currency": "USD",
    "payment_method": "Credit Card",
    "payment_date": "2024-01-16T10:30:00",
    "notes": "Payment for Premium Job Posting Package",
    "created_at": "2024-01-15T09:00:00",
    "updated_at": "2024-01-16T10:30:00",
    "line_items": [
      {
        "id": 1,
        "description": "Premium Job Posting Package",
        "quantity": 1,
        "unit_price": 299.00,
        "total_price": 299.00,
        "job_id": 1,
        "job_title": "Senior Software Engineer",
        "package_type": "premium"
      }
    ],
    "state": "posted",
    "payment_state": "paid",
    "ref": "SO001",
    "origin": "Sales Order SO001"
  }
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Missing or invalid Authorization header"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": "Access denied - You can only view your own invoices"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Invoice not found"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Error message",
  "data": [],
  "total": 0,
  "limit": 10,
  "offset": 0
}
```

## Usage Examples

### Python Example

```python
import requests
import json

# Get authentication token first
login_url = "http://localhost:8069/angkort/api/v1/login"
login_data = {
    "username": "admin",
    "password": "admin"
}
login_response = requests.post(login_url, json=login_data)
token = login_response.json()['data']['access_token']

# Get invoices
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# List invoices
invoices_url = "http://localhost:8069/api/invoices"
response = requests.get(invoices_url, headers=headers, params={
    "limit": 10,
    "status": "paid"
})
invoices = response.json()

# Get specific invoice
invoice_url = "http://localhost:8069/api/invoices/1"
response = requests.get(invoice_url, headers=headers)
invoice = response.json()
```

### JavaScript Example

```javascript
// Get authentication token first
const loginResponse = await fetch('http://localhost:8069/angkort/api/v1/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin'
  })
});
const { data } = await loginResponse.json();
const token = data.access_token;

// Get invoices
const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};

// List invoices
const invoicesResponse = await fetch('http://localhost:8069/api/invoices?limit=10&status=paid', {
  headers
});
const invoices = await invoicesResponse.json();

// Get specific invoice
const invoiceResponse = await fetch('http://localhost:8069/api/invoices/1', {
  headers
});
const invoice = await invoiceResponse.json();
```

## Security Considerations

1. **Bearer Token Authentication**: All endpoints require valid tokens using Odoo's `angkit` auth method
2. **Role-Based Access**: Users can only access invoices they're authorized to see
3. **Input Validation**: All parameters are validated before processing
4. **SQL Injection Protection**: Uses Odoo's ORM for safe database queries
5. **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

## Implementation Notes

- The endpoints use Odoo's `account.move` model for invoice data
- Only customer invoices (`out_invoice`, `out_refund`) are returned
- The API uses `sudo()` to bypass access rights for public endpoints while maintaining role-based filtering
- All date fields are returned in ISO format
- Currency information is included for proper display
- Line items include job-related information when available

## Testing

Use the provided `test_invoice_api.py` script to test the endpoints:

```bash
python test_invoice_api.py
```

Make sure to update the configuration variables in the script before running.
