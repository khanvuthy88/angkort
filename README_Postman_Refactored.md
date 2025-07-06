# Angkort API - Refactored Postman Collection

This document provides instructions for using the refactored Postman collection with form-data requests and Bearer Token authorization.

## Files

- `Angkort_API_Collection_Refactored.json` - Main Postman collection
- `Angkort_API_Environment.json` - Postman environment with variables

## Setup Instructions

### 1. Import Collection and Environment

1. Open Postman
2. Click **Import** button
3. Import both files:
   - `Angkort_API_Collection_Refactored.json`
   - `Angkort_API_Environment.json`

### 2. Configure Environment

1. Select the **"Angkort API Environment"** from the environment dropdown
2. Update the following variables:
   - `baseUrl`: Your Odoo server URL (default: `http://localhost:8069`)
   - `username`: Your Odoo username (default: `admin`)
   - `password`: Your Odoo password (default: `admin`)
   - `api_key`: Leave empty (will be filled after login)

### 3. Authentication Flow

#### Step 1: Login
1. Go to **Authentication** folder
2. Select **"Login"** request
3. Update username and password in the request body if needed
4. Send the request
5. Copy the `access_token` from the response

#### Step 2: Set Bearer Token
1. In the environment variables, set `api_key` to the copied token
2. The collection is configured to automatically use this token for all requests

## Key Changes from Original Collection

### 🔄 Request Body Format
- **Changed from JSON to form-data**: All POST/PUT requests now use `application/x-www-form-urlencoded`
- **File uploads**: Use `multipart/form-data` for image uploads
- **Array parameters**: Use bracket notation (e.g., `cart[0][product_id]`)

### 🔐 Authorization
- **Bearer Token**: Collection-level authorization using `{{api_key}}` variable
- **Automatic token usage**: All requests automatically include the Bearer token
- **Secure token storage**: Token stored as environment variable

### 📋 Request Examples

#### Login Request
```http
POST {{baseUrl}}/angkort/api/v1/login
Content-Type: application/x-www-form-urlencoded

username={{username}}&password={{password}}
```

#### Create Product with Image
```http
POST {{baseUrl}}/angkort/api/v1/shop/{{shop_id}}/product
Content-Type: multipart/form-data
Authorization: Bearer {{api_key}}

name=Product Name
list_price=10.0
categ_id=1
description=Product description
image=[file upload]
```

#### Create Order with Multiple Items
```http
POST {{baseUrl}}/angkort/api/v1/order
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer {{api_key}}

partner_id=1&order_lines[0][product_id]=1&order_lines[0][quantity]=2&order_lines[1][product_id]=2&order_lines[1][quantity]=1
```

## Environment Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `baseUrl` | Odoo server URL | `http://localhost:8069` |
| `api_key` | Bearer token for authentication | (empty) |
| `username` | Odoo username | `admin` |
| `password` | Odoo password | `admin` |
| `shop_id` | Default shop ID for requests | `1` |
| `product_id` | Default product ID for requests | `1` |
| `category_id` | Default category ID for requests | `1` |
| `variant_id` | Default variant ID for requests | `1` |
| `order_id` | Default order ID for requests | `1` |

## Request Categories

### 🔐 Authentication
- **Login**: Authenticate and get access token
- **Logout**: Invalidate current token

### 📦 Order Management
- **Get My Orders**: List user's orders with pagination
- **Get My Order Detail**: Get specific order details
- **Cart Checkout**: Validate cart and check stock
- **Create Order (Global)**: Create new sale order

### 🏪 Shop Management
- **List Shops**: Get all shops with pagination
- **Get Shop Detail**: Get specific shop details
- **Create Shop**: Create new shop
- **Update Shop**: Update existing shop
- **Delete Shop**: Delete shop

### 📦 Product Management
- **List Products**: Get shop products with pagination
- **Get Product Detail**: Get specific product details
- **Create Product**: Create new product (supports image upload)
- **Update Product**: Update existing product
- **Delete Product**: Delete product
- **Calculate Product Price**: Calculate price with variants

### 🏷️ Category Management
- **List Categories**: Get shop categories
- **Create Category**: Create new category
- **Update Category**: Update existing category
- **Delete Category**: Delete category

### 🔧 Variant Management
- **List Variants**: Get product variants
- **Create Variant**: Create new variant
- **Update Variant**: Update existing variant
- **Delete Variant**: Delete variant
- **List Variant Values**: Get variant values
- **Create Variant Value**: Create new variant value

### 🛠️ Other Endpoints
- **Industries**: Get all industries
- **Image Upload**: Upload and process images
- **Global Sale Orders**: Get all sale orders
- **Global Product Variants**: Get all product variants

## Testing Workflow

### 1. Initial Setup
1. Import collection and environment
2. Configure environment variables
3. Test login endpoint

### 2. Authentication
1. Send login request
2. Copy access token from response
3. Set `api_key` environment variable
4. Verify token works with a simple GET request

### 3. CRUD Operations
1. **Create**: Test creating shops, products, categories
2. **Read**: Test listing and getting details
3. **Update**: Test updating existing records
4. **Delete**: Test deleting records

### 4. File Uploads
1. Test image upload for products
2. Verify image processing and storage

### 5. Complex Operations
1. Test order creation with multiple items
2. Test price calculation with variants
3. Test cart checkout functionality

## Troubleshooting

### Common Issues

#### 401 Unauthorized
- Check if `api_key` is set correctly
- Verify token hasn't expired
- Re-login to get a new token

#### 400 Bad Request
- Check form-data format
- Verify required fields are included
- Check data types (numbers vs strings)

#### 404 Not Found
- Verify resource IDs exist
- Check URL path parameters
- Ensure shop_id/product_id are valid

#### CORS Issues
- Verify `baseUrl` is correct
- Check if Odoo server is running
- Ensure CORS is configured on server

### Debug Tips

1. **Check Environment Variables**: Verify all variables are set correctly
2. **Inspect Request Headers**: Ensure Content-Type and Authorization are correct
3. **Review Response**: Check error messages in response body
4. **Test with Simple Requests**: Start with GET requests before POST/PUT
5. **Use Postman Console**: Enable console to see detailed request/response logs

## Security Notes

- **Token Security**: Never commit tokens to version control
- **Environment Variables**: Use environment variables for sensitive data
- **HTTPS**: Use HTTPS in production environments
- **Token Expiry**: Implement token refresh logic for long-running tests

## Migration from Original Collection

If migrating from the original JSON-based collection:

1. **Update Request Bodies**: Change from JSON to form-data format
2. **Set Authorization**: Configure Bearer token authentication
3. **Update Variables**: Use new environment variable names
4. **Test All Endpoints**: Verify all requests work with new format

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify Odoo server configuration
3. Review API documentation in the controller code
4. Test with simple requests first 