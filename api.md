# Angkort API Documentation

## Base URL

All API endpoints are prefixed with: `/angkort/api/v1`

## Authentication

- Most endpoints require authentication using the `angkit` auth method
- Some endpoints are public and don't require authentication

## Endpoints

### Shop Management

#### Get All Shops

```http
GET /shop
```

**Authentication**: Public

**Response**: List of shops with their details

```json
[
  {
    "id": 123,
    "name": "My Shop",
    "phoneNumber": ["+1234567890"],
    "address": ["123 Main St"],
    "wifi": ["Shop_WiFi"],
    "banks": [
      {
        "bank_name": "Bank A",
        "account_number": "1234567890"
      }
    ]
  }
]
```

#### Get Shop Details

```http
GET /shop/{shop_id}
```

**Authentication**: Public

**Parameters**:

- `shop_id` (int): ID of the shop

**Response**: Detailed shop information

```json
{
  "id": 123,
  "name": "My Shop",
  "phoneNumber": ["+1234567890"],
  "address": ["123 Main St"],
  "wifi": ["Shop_WiFi"],
  "banks": [
    {
      "bank_name": "Bank A",
      "account_number": "1234567890"
    }
  ]
}
```

#### Create Shop

```http
POST /shop/create
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "params": {
    "name": "Shop Name",
    "phone": "1234567890",
    "wifi_name": "Shop_WiFi",
    "customer_address": "123 Main St",
    "email": "shop@example.com"
  }
}
```

**Response**:

```json
{
  "status": true,
  "shop_data": {
    "name": "Shop Name",
    "id": 123
  }
}
```

#### Update Shop

```http
POST /shop/update
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "id": 123,
  "name": "Updated Shop Name",
  "phone": "1234567890",
  "wifi_name": "New_WiFi",
  "customer_address": "456 New St"
}
```

**Response**:

```json
{
  "status": true,
  "message": "Shop with ID 123 updated successfully"
}
```

### Product Management

#### Get Product Details

```http
GET /shop/{shop_id}/product/{product_id}
```

**Authentication**: Public

**Parameters**:

- `shop_id` (int): ID of the shop
- `product_id` (int): ID of the product

**Response**:

```json
{
  "id": 123,
  "name": "Product Name",
  "price": 99.99,
  "description": "Product description",
  "image": "http://example.com/image.jpg",
  "options": [
    {
      "id": 1,
      "name": "Size",
      "data": [
        { "id": 1, "name": "Small", "price": 0 },
        { "id": 2, "name": "Large", "price": 5 }
      ]
    }
  ],
  "choices": [
    {
      "id": 2,
      "name": "Toppings",
      "data": [
        { "id": 3, "name": "Extra Cheese", "price": 2 },
        { "id": 4, "name": "Bacon", "price": 3 }
      ]
    }
  ]
}
```

#### Get All Products

```http
GET /shop/{shop_id}/product
```

**Authentication**: Public

**Parameters**:

- `shop_id` (int): ID of the shop

**Response**: List of products with their details

#### Create Product

```http
POST /shop/{shop_id}/product/create
```

**Authentication**: Required (angkit)

**Content-Type**: multipart/form-data

**Parameters**:

- `shop_id` (int): ID of the shop

**Form Data**:

- `name` (str): Product name
- `price` (float): Product price
- `category_id` (int): Category ID
- `image` (file): Product image
- `description` (str): Product description
- `barcode` (str): Product barcode
- `qty_available` (float): Initial quantity
- `attributes` (json): Product attributes and values
  ```json
  {
    "attributes": [
      {
        "attribute_id": 1,
        "values": [
          {
            "value_id": 1,
            "extra_price": 2.5
          },
          {
            "value_id": 2,
            "extra_price": 3.0
          }
        ]
      }
    ]
  }
  ```

**Response**:

```json
{
  "status": true,
  "message": "Product created successfully"
}
```

#### Update Product

```http
POST /shop/{shop_id}/product/{product_id}/update
```

**Authentication**: Required (angkit)

**Content-Type**: multipart/form-data

**Parameters**:

- `shop_id` (int): ID of the shop
- `product_id` (int): ID of the product

**Form Data**:

- `name` (str): Product name
- `price` (float): Product price
- `category_id` (int): Category ID
- `image` (file): Product image
- `description` (str): Product description
- `barcode` (str): Product barcode
- `qty_available` (float): Initial quantity
- `attributes` (json): Product attributes and values
  ```json
  {
    "attributes": [
      {
        "attribute_id": 1,
        "values": [
          {
            "value_id": 1,
            "extra_price": 2.5
          },
          {
            "value_id": 2,
            "extra_price": 3.0
          }
        ]
      }
    ]
  }
  ```

**Response**:

```json
{
  "status": "success",
  "message": "Product updated successfully",
  "product": {
    "id": 123,
    "name": "Updated Product",
    "price": 99.99,
    "category_id": 456,
    "attributes": [
      {
        "attribute_id": 1,
        "attribute_name": "Size",
        "values": [
          {
            "value_id": 1,
            "value_name": "Small",
            "extra_price": 2.5
          },
          {
            "value_id": 2,
            "value_name": "Large",
            "extra_price": 3.0
          }
        ]
      }
    ]
  }
}
```

#### Delete Product

```http
POST /shop/{shop_id}/product/{product_id}/delete
```

**Authentication**: Required (angkit)

**Parameters**:

- `shop_id` (int): ID of the shop
- `product_id` (int): ID of the product

**Response**:

```json
{
  "status": true,
  "message": "Product deleted successfully"
}
```

### Product Categories

#### Get Categories

```http
GET /shop/{shop_id}/product/category
```

**Authentication**: Public

**Parameters**:

- `shop_id` (int): ID of the shop

**Response**: List of categories

#### Create Category

```http
POST /shop/{shop_id}/product/category/create
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "name": "New Category"
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Category created successfully",
  "category": {
    "id": 123,
    "name": "New Category"
  }
}
```

#### Update Category

```http
POST /shop/{shop_id}/product/category/{cate_id}/update
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "name": "Updated Category Name",
  "shop_id": 123
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Category updated successfully",
  "category": {
    "id": 456,
    "name": "Updated Category Name"
  }
}
```

#### Delete Category

```http
POST /shop/{shop_id}/product/category/{cate_id}/delete
```

**Authentication**: Required (angkit)

**Parameters**:

- `shop_id` (int): ID of the shop
- `cate_id` (int): ID of the category

**Response**:

```json
{
  "status": "success",
  "message": "Category deleted successfully"
}
```

### Product Variants

#### Get Variants

```http
GET /shop/{shop_id}/product/variant/
```

**Authentication**: Required (angkit)

**Parameters**:

- `shop_id` (int): ID of the shop

**Response**: List of product attributes

#### Create Variant

```http
POST /shop/{shop_id}/product/variant/create
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "create_variant": "no_variant",
  "display_type": "multi",
  "name": "Extras",
  "visibility": "visible"
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Attribute created successfully",
  "attribute": {
    "id": 1,
    "name": "Extras",
    "create_variant": "no_variant",
    "display_type": "multi"
  }
}
```

#### Update Variant

```http
POST /shop/{shop_id}/product/variant/update/{variant_id}
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "name": "Updated Size",
  "create_variant": "always",
  "display_type": "radio",
  "sequence": 2
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Attribute updated successfully",
  "attribute": {
    "id": 1,
    "name": "Updated Size",
    "create_variant": "always",
    "display_type": "radio",
    "sequence": 2
  }
}
```

#### Delete Variant

```http
DELETE /shop/{shop_id}/product/variant/delete/{variant_id}
```

**Authentication**: Required (angkit)

**Parameters**:

- `shop_id` (int): ID of the shop
- `variant_id` (int): ID of the variant

**Response**:

```json
{
  "status": "success",
  "message": "Attribute deleted successfully"
}
```

### Variant Values

#### Create Variant Value

```http
POST /shop/{shop_id}/product/variant/value
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "attribute_id": 1,
  "values": [
    {
      "name": "Extra Cheese",
      "extra_price": 2.5
    },
    {
      "name": "Extra Bacon",
      "extra_price": 3.0
    }
  ]
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Attribute values created successfully"
}
```

#### Update Variant Value

```http
PUT /shop/{shop_id}/product/variant/value/{value_id}
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "name": "Updated Value",
  "extra_price": 4.0
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Variant value updated successfully"
}
```

### Order Management

#### Get My Orders

```http
GET /my/order
```

**Authentication**: Required (angkit)

**Response**: Orders grouped by state

```json
{
  "draft": [
    {
      "id": 123,
      "name": "SO123",
      "date_order": "01-01-2024",
      "total": 199.99,
      "state": "Quotation"
    }
  ],
  "sale": [
    {
      "id": 124,
      "name": "SO124",
      "date_order": "02-01-2024",
      "total": 299.99,
      "state": "Sale Order"
    }
  ]
}
```

#### Get Order Details

```http
GET /my/order/{order_id}
```

**Authentication**: Required (angkit)

**Parameters**:

- `order_id` (int): ID of the order

**Response**:

```json
{
  "id": 123,
  "partner_id": 456,
  "partner_name": "John Doe",
  "delivery_address": "123 Main St, City, Country",
  "name": "SO123",
  "date_order": "01-01-2024",
  "total": 199.99,
  "state": "draft",
  "order_lines": [
    {
      "product_id": 789,
      "name": "Product Name",
      "code": "PROD001",
      "quantity": 2,
      "price_unit": 99.99
    }
  ]
}
```

### Cart Management

#### Checkout Cart

```http
POST /cart/checkout
```

**Authentication**: Required (angkit)

**Request Body**:

```json
{
  "cart": [
    {
      "product_id": 123,
      "quantity": 2
    }
  ]
}
```

**Response**:

```json
{
  "status": "sufficient_stock",
  "details": [
    {
      "product_id": 123,
      "code": "PROD001",
      "name": "Product Name",
      "quantity": 2,
      "sub_total": 199.98
    }
  ],
  "total_amount": 199.98
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "status": "error",
  "message": "Error message here"
}
```

### 404 Not Found

```json
{
  "status": "error",
  "message": "Resource not found"
}
```

### 500 Internal Server Error

```json
{
  "status": "error",
  "message": "Internal server error"
}
```
