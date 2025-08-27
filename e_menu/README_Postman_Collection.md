# e_menu Controllers Postman Collection

This Postman collection contains all the API endpoints available in the `e_menu/controllers` module of the Angkort Odoo project.

## Files

- **Postman_Collection_e_menu_Controllers.json** - The main Postman collection file
- **Postman_Environment_e_menu_Controllers.json** - Environment variables file
- **README_Postman_Collection.md** - This documentation file

## Installation

1. **Import the Collection:**
   - Open Postman
   - Click "Import" button
   - Select `Postman_Collection_e_menu_Controllers.json`

2. **Import the Environment:**
   - Click "Import" button again
   - Select `Postman_Environment_e_menu_Controllers.json`
   - Select the imported environment from the dropdown in the top-right corner

## Environment Variables

The collection uses the following environment variables:

### Base Configuration
- `base_url` - Your Odoo server URL (default: http://localhost:8069)
- `api_version` - API version (default: v1)

### Authentication
- `access_token` - JWT access token for authenticated requests
- `refresh_token` - JWT refresh token
- `username` - Odoo username (default: admin)
- `password` - Odoo password (default: admin)

### Entity IDs
- `shop_id` - Shop ID for shop-specific operations
- `product_id` - Product ID for product operations
- `variant_id` - Product variant ID
- `value_id` - Variant value ID
- `order_id` - Order ID
- `wifi_id` - WiFi configuration ID
- `hour_id` - Opening hours ID
- `employee_id` - Employee ID for HR operations

### Telegram
- `telegram_token` - Telegram bot token
- `chat_id` - Telegram chat ID

## API Endpoints Overview

### 1. Authentication
- **POST** `/angkort/api/v1/auth/login` - User login
- **POST** `/angkort/api/v1/auth/refresh` - Refresh access token
- **POST** `/angkort/api/v1/auth/logout` - User logout

### 2. Orders
- **GET** `/angkort/api/v1/my/order` - Get user's orders (paginated)
- **GET** `/angkort/api/v1/my/order/{order_id}` - Get specific order details
- **POST** `/angkort/api/v1/cart/checkout` - Validate cart items
- **GET** `/angkort/api/v1/sale` - Get global sale orders (paginated)
- **POST** `/angkort/api/v1/order` - Create new global order

### 3. Shops
- **GET** `/angkort/api/v1/shop` - Get shop list (paginated)
- **GET** `/angkort/api/v1/shop/{shop_id}` - Get shop details
- **POST** `/angkort/api/v1/shop` - Create new shop
- **PUT** `/angkort/api/v1/shop/{shop_id}` - Update shop
- **PATCH** `/angkort/api/v1/shop/{shop_id}` - Partially update shop
- **DELETE** `/angkort/api/v1/shop/{shop_id}` - Delete shop
- **POST** `/angkort/api/v1/shop/create` - Alternative shop creation

### 4. Shop WiFi
- **POST** `/angkort/api/v1/shop/{shop_id}/wifi` - Create WiFi configuration
- **PUT** `/angkort/api/v1/shop/{shop_id}/wifi/{wifi_id}` - Update WiFi
- **DELETE** `/angkort/api/v1/shop/{shop_id}/wifi/{wifi_id}` - Delete WiFi

### 5. Shop Opening Hours
- **POST** `/angkort/api/v1/shop/{shop_id}/open-hours` - Create opening hours
- **PUT** `/angkort/api/v1/shop/{shop_id}/open-hours/{hour_id}` - Update opening hours
- **DELETE** `/angkort/api/v1/shop/{shop_id}/open-hours/{hour_id}` - Delete opening hours

### 6. Shop Banner
- **POST** `/angkort/api/v1/shop/{shop_id}/banner` - Update shop banner

### 7. Products
- **GET** `/angkort/api/v1/shop/{shop_id}/product` - Get shop products (paginated)
- **GET** `/angkort/api/v1/product` - Get global products (paginated)
- **GET** `/angkort/api/v1/product/{product_id}` - Get product details

### 8. Product Categories
- **GET** `/angkort/api/v1/product/category` - Get product categories (paginated)

### 9. Product Variants
- **GET** `/angkort/api/v1/product/variant` - Get global variants (paginated)
- **GET** `/angkort/api/v1/shop/{shop_id}/product/variant` - Get shop variants
- **POST** `/angkort/api/v1/shop/{shop_id}/product/variant` - Create variant
- **PUT** `/angkort/api/v1/shop/{shop_id}/product/variant/{variant_id}` - Update variant
- **PATCH** `/angkort/api/v1/shop/{shop_id}/product/variant/{variant_id}` - Patch variant
- **DELETE** `/angkort/api/v1/shop/{shop_id}/product/variant/{variant_id}` - Delete variant

### 10. Variant Values
- **GET** `/angkort/api/v1/shop/{shop_id}/product/{variant_id}/value` - Get variant values
- **POST** `/angkort/api/v1/shop/{shop_id}/product/variant/value` - Create variant values
- **PUT** `/angkort/api/v1/shop/{shop_id}/product/variant/value/{value_id}` - Update variant value
- **PATCH** `/angkort/api/v1/shop/{shop_id}/product/variant/value/{value_id}` - Patch variant value
- **DELETE** `/angkort/api/v1/shop/{shop_id}/product/variant/value/{value_id}` - Delete variant value

### 11. Images
- **POST** `/angkort/api/v1/image/add` - Upload and process images

### 12. Partners
- **GET** `/angkort/api/v1/store` - Get partners/stores (paginated)

### 13. HR
- **GET** `/angkort/api/v1/hr/employee/{employee_id}/skills` - Get employee skills
- **GET** `/angkort/api/v1/hr/employee/{employee_id}/resume` - Get employee resume

### 14. Telegram
- **POST** `/angkort/api/v1/telegram/webhook/{token}/{chat_id}` - Telegram webhook

### 15. Test
- **GET** `/angkort/api/v1/test` - Test HTTP endpoint
- **POST** `/angkort/api/v1/test` - Test JSON endpoint

## Usage Examples

### 1. Authentication Flow
1. Set your `username` and `password` in environment variables
2. Call the **Login** endpoint
3. Copy the `access_token` from the response to your environment variables
4. Use the token for subsequent authenticated requests

### 2. Creating a Shop
1. Ensure you have a valid `access_token`
2. Use the **Create Shop** endpoint with form-data
3. Copy the returned `shop_id` to your environment variables
4. Use this `shop_id` for shop-specific operations

### 3. Managing Products
1. Set `shop_id` in environment variables
2. Create product variants using **Create Product Variant**
3. Copy the returned `variant_id` to environment variables
4. Create variant values using **Create Variant Values**
5. Copy the returned `value_id` to environment variables

## Query Parameters

Most list endpoints support the following query parameters:

### Pagination
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)

### Search & Filtering
- `search` - Search term for text fields
- `sort` - Field to sort by
- `order` - Sort order (asc/desc)
- `filter_*` - Various filter parameters

### Examples
```
GET /angkort/api/v1/shop?page=1&limit=10&search=coffee&sort=name&order=asc
GET /angkort/api/v1/product?filter_category=1&filter_price_min=10&filter_price_max=100
```

## Authentication

The collection uses Bearer token authentication. After login:

1. The `access_token` is automatically used in the Authorization header
2. For protected endpoints, ensure `access_token` is set in environment variables
3. If token expires, use the **Refresh Token** endpoint to get a new one

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `201` - Created
- `204` - No Content (for deletions)
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## File Uploads

For file uploads (images, banners), use `formdata` body mode:

```json
{
  "key": "image",
  "type": "file",
  "src": []
}
```

## Testing

1. **Test Authentication:**
   - Use the **Test HTTP Endpoint** to verify server connectivity
   - Test login with valid credentials

2. **Test CRUD Operations:**
   - Create a shop
   - Update shop details
   - Delete the shop

3. **Test File Uploads:**
   - Upload an image using the **Upload Image** endpoint
   - Update shop banner with an image file

## Troubleshooting

### Common Issues

1. **401 Unauthorized:**
   - Check if `access_token` is set
   - Verify token hasn't expired
   - Use refresh token if needed

2. **404 Not Found:**
   - Verify entity IDs in environment variables
   - Check if the resource exists

3. **400 Bad Request:**
   - Verify required fields are provided
   - Check data format (JSON vs form-data)
   - Validate field values

4. **500 Internal Server Error:**
   - Check server logs
   - Verify database connectivity
   - Check Odoo module installation

### Debug Tips

1. **Check Environment Variables:**
   - Ensure all required variables are set
   - Verify variable values are correct

2. **Monitor Network Tab:**
   - Check request/response headers
   - Verify authentication tokens

3. **Test with Simple Endpoints:**
   - Start with public endpoints
   - Gradually test authenticated endpoints

## Support

For issues with the API endpoints, check:
1. Odoo server logs
2. Module installation status
3. Database configuration
4. Network connectivity

## Notes

- All timestamps are in ISO 8601 format
- File uploads support common image formats
- Pagination is consistent across all list endpoints
- Search functionality supports partial text matching
- Filtering supports various data types (strings, numbers, booleans)
