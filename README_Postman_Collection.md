# Angkort API Postman Collection

This document explains how to use the automatically generated Postman collection for the Angkort Odoo API.

## 📁 Generated Files

- `Angkort_API_Collection.json` - Basic Postman collection
- `Angkort_API_Collection_Improved.json` - Improved Postman collection with better URL parsing
- `generate_postman_collection.py` - Script to generate basic collection
- `generate_postman_collection_improved.py` - Script to generate improved collection

## 🚀 Quick Start

### 1. Import the Collection

1. Open **Postman**
2. Click **Import** button
3. Select `Angkort_API_Collection_Improved.json`
4. The collection will be imported with all endpoints organized by controller

### 2. Configure Environment Variables

After importing, set up the following variables in your Postman environment:

| Variable | Value | Description |
|----------|-------|-------------|
| `base_url` | `http://localhost:8069` | Your Odoo server URL |
| `access_token` | `your_access_token_here` | Authentication token for protected endpoints |

### 3. Test the API

- **Public endpoints** can be tested immediately
- **Authenticated endpoints** require setting the `access_token` variable
- **Path parameters** (like `{shop_id}`, `{product_id}`) need to be set in the request URL

## 📋 API Endpoints Overview

The collection is organized into the following folders:

### 🏪 Controllers
- Shop management endpoints
- Product category operations
- Industry listings
- Login functionality

### 👥 HR Controller
- Employee management
- Employee details with skills and resume

### 🛍️ Shop Controller
- Shop CRUD operations
- Product management
- Order management
- Cart operations
- Product variants and attributes

## 🔧 Authentication

### Public Endpoints
These endpoints don't require authentication:
- `GET /angkort/api/v1/industries`
- `GET /angkort/api/v1/product/category`
- `GET /angkort/api/v1/shop/{shop_id}/product`

### Authenticated Endpoints
These endpoints require a Bearer token:
- `POST /angkort/api/v1/shop/create`
- `GET /angkort/api/v1/my/order`
- `POST /angkort/api/v1/shop/{shop_id}/product/create`

## 📝 Example Usage

### 1. Get All Industries
```
GET {{base_url}}/angkort/api/v1/industries
```

### 2. Create a Shop (Authenticated)
```
POST {{base_url}}/angkort/api/v1/shop/create
Headers:
  Authorization: Bearer {{access_token}}
  Content-Type: application/json

Body:
{
  "params": {
    "name": "My Shop",
    "phone": "+1234567890",
    "wifi_name": "Shop_WiFi",
    "customer_address": "123 Main St"
  }
}
```

### 3. Get Shop Products
```
GET {{base_url}}/angkort/api/v1/shop/{{shop_id}}/product
```

## 🔄 Regenerating the Collection

If you add new endpoints to your Odoo controllers, you can regenerate the collection:

```bash
python3 generate_postman_collection_improved.py
```

This will:
1. Scan all controller files in `e_menu/controllers/`
2. Extract route decorators and docstrings
3. Parse authentication, methods, and parameters
4. Generate a new Postman collection JSON file

## 📊 Collection Statistics

- **Total Endpoints**: 34
- **Controllers**: 3 (Controllers, HR Controller, Shop Controller)
- **HTTP Methods**: GET, POST, PUT, DELETE
- **Authentication Types**: Public, angkit (Bearer token)

## 🛠️ Customization

### Adding New Endpoints
1. Add your endpoint to a controller file
2. Include proper docstring documentation
3. Use the `@http.route` decorator
4. Regenerate the collection

### Example Controller Endpoint
```python
@http.route(f"{BASE_URL}/example", auth="public", type="json", cors="*")
def example_endpoint(self):
    """
    Example endpoint description.
    
    Endpoint: GET /angkort/api/v1/example
    Auth: Public
    
    Returns:
        dict: Example response
            {
                "status": "success",
                "message": "Example response"
            }
    """
    return {"status": "success", "message": "Example response"}
```

## 🐛 Troubleshooting

### Common Issues

1. **URL not found**: Check that `base_url` variable is set correctly
2. **Authentication failed**: Ensure `access_token` is valid and set
3. **Path parameters**: Replace `{shop_id}`, `{product_id}` etc. with actual values
4. **CORS errors**: Most endpoints include CORS headers, but check server configuration

### Debugging Tips

1. Use Postman's **Console** to see request/response details
2. Check **Network** tab in browser developer tools
3. Verify Odoo server is running and accessible
4. Test with a simple public endpoint first

## 📚 Additional Resources

- [Postman Documentation](https://learning.postman.com/)
- [Odoo HTTP Controllers](https://www.odoo.com/documentation/16.0/developer/reference/addons/http.html)
- [Angkort Project Documentation](link-to-your-docs)

---

**Generated on**: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
**Odoo Version**: 18.0
**API Base URL**: `/angkort/api/v1` 