# Angkort API Deep Review + Request Samples

Date: 2026-02-16
Scope reviewed from source code:
- `/Users/khanvuthy/Documents/odoo/odoo18-project/angkort/e_menu/controllers/api/auth.py`
- `/Users/khanvuthy/Documents/odoo/odoo18-project/angkort/e_menu/controllers/api/shop.py`
- `/Users/khanvuthy/Documents/odoo/odoo18-project/angkort/e_menu/controllers/api/product.py`
- `/Users/khanvuthy/Documents/odoo/odoo18-project/angkort/e_menu/controllers/api/order.py`
- `/Users/khanvuthy/Documents/odoo/odoo18-project/angkort/e_menu/controllers/api/utils.py`

Base URL: `/angkort/api/v1`

## 1) API Surface Summary

Total routes reviewed: 41

- Auth: 4
- Shop: 22
- Product/Variant/Image: 18
- Order: 7

Auth types used:
- `auth="public"`: public access
- `auth="none"`: no auth session required (login/refresh)
- `auth="angkit"`: bearer token required (custom auth)

Ownership checks are enforced via `@verify_ownership(...)` on write endpoints for:
- `shop`, `wifi`, `open_hour`, `bank`, `banner`, `variant`, `variant_value`

## 2) Response/Validation Pattern (Observed)

The API uses mixed response envelopes:
- Plain object data: `{...}`
- Wrapped data: `{ "data": {...}, "meta": {...} }`
- Error styles vary:
  - `{ "error": "..." }`
  - `{ "status": "error", "message": "...", "errors": [...] }`

Status behavior is generally REST-like:
- `200` success read/update
- `201` created
- `204` delete success
- `400` validation/input errors
- `401` auth failure
- `403` ownership/authorization failure
- `404` not found
- `500` unhandled/internal

## 3) Endpoints Supporting Both JSON and Form

The following endpoints explicitly accept both JSON and form-style input:
- `POST /login`
- `POST /register`
- `POST /shop/create`
- `POST /shop/{shop_id}/bank`
- `PUT /shop/{shop_id}/bank/{bank_id}`
- `POST /shop/{shop_id}/category`
- `POST /shop/{shop_id}/product`
- `PUT /shop/{shop_id}/product/{product_id}`
- `PATCH /shop/{shop_id}/product/{product_id}`
- `PUT /shop/{shop_id}/product/variant/{variant_id}`
- `PATCH /shop/{shop_id}/product/variant/{variant_id}`

Most other write endpoints are effectively form-only or json-only based on implementation.

## 4) Sample Payloads (JSON + Form)

### 4.1 Login

JSON
```json
{
  "username": "merchant@example.com",
  "password": "secret123"
}
```

Form (`x-www-form-urlencoded`)
- `username`: `merchant@example.com`
- `password`: `secret123`

### 4.2 Register

JSON
```json
{
  "name": "Demo Merchant",
  "username": "demo.merchant@example.com",
  "password": "secret123"
}
```

Form (`x-www-form-urlencoded`)
- `name`: `Demo Merchant`
- `username`: `demo.merchant@example.com`
- `password`: `secret123`

### 4.3 Shop Create (`/shop/create`)

JSON
```json
{
  "name": "Angkor Coffee",
  "phone": "+85512345678",
  "customer_address": "Phnom Penh",
  "email": "shop@example.com",
  "shop_latitude": 11.5564,
  "shop_longitude": 104.9282,
  "wifi_name": "GuestWifi"
}
```

Form (`x-www-form-urlencoded`)
- `name`: `Angkor Coffee`
- `phone`: `+85512345678`
- `customer_address`: `Phnom Penh`
- `email`: `shop@example.com`

### 4.4 Shop Bank Create

JSON
```json
{
  "name": "ABA Bank",
  "code": "0011223344",
  "currency": "USD",
  "link": "https://pay.example.com/aba/0011223344",
  "sequence": 10,
  "active": true
}
```

Form (`multipart/form-data`)
- `name`: `ABA Bank`
- `code`: `0011223344`
- `currency`: `USD`
- `link`: `https://pay.example.com/aba/0011223344`
- `sequence`: `10`
- `active`: `true`
- `logo`: `(file, optional)`

### 4.5 Shop Bank Update

JSON
```json
{
  "name": "ABA Business",
  "currency": "KHR",
  "active": false,
  "sequence": 20
}
```

Form (`multipart/form-data`)
- `name`: `ABA Business`
- `currency`: `KHR`
- `active`: `false`
- `sequence`: `20`
- `logo`: `(file, optional)`

### 4.6 Shop Category Create

JSON
```json
{
  "name": "Drinks",
  "parent_id": 12
}
```

Form (`x-www-form-urlencoded`)
- `name`: `Drinks`
- `parent_id`: `12`

### 4.7 Product Create

JSON
```json
{
  "name": "Iced Latte",
  "type": "consu",
  "code": "LATTE-ICED-01",
  "description": "Double shot iced latte",
  "sale_price": 3.5,
  "category_id": 5,
  "variant_ids": [1],
  "attribute_lines": [
    {
      "attribute_id": 1,
      "value_ids": [11, 12]
    }
  ]
}
```

Form (`multipart/form-data`)
- `name`: `Iced Latte`
- `type`: `consu`
- `code`: `LATTE-ICED-01`
- `description`: `Double shot iced latte`
- `sale_price`: `3.5`
- `category_id`: `5`
- `variant_ids`: `[1]`
- `attribute_lines`: `[{"attribute_id":1,"value_ids":[11,12]}]`
- `image`: `(file, optional)`

### 4.8 Product Update (PUT)

JSON
```json
{
  "name": "Iced Latte Large",
  "type": "consu",
  "sale_price": 4.5,
  "code": "LATTE-01"
}
```

### 4.9 Product Patch (PATCH)

JSON
```json
{
  "sale_price": 4.0
}
```

### 4.10 Product Delete (DELETE)

Method: `DELETE`
Path: `/shop/1/product/55`
Response: `204 No Content`

### 4.11 Variant Update (PUT)

JSON
```json
{
  "name": "Size",
  "create_variant": "always",
  "display_type": "radio"
}
```

Form (`x-www-form-urlencoded`)
- `name`: `Size`
- `create_variant`: `always`
- `display_type`: `radio`

### 4.9 Variant Patch (PATCH)

JSON
```json
{
  "name": "Size (Updated)",
  "display_type": "radio"
}
```

Form (`x-www-form-urlencoded`)
- `name`: `Size (Updated)`
- `display_type`: `radio`

### 4.10 Orders

Create my order (`POST /my/order`) JSON only
```json
{
  "order_lines": [
    { "product_id": 101, "quantity": 2, "price_unit": 3.5 },
    { "product_id": 202, "quantity": 1 }
  ],
  "note": "No sugar"
}
```

Global order (`POST /order`) JSON only
```json
{
  "partner_id": 1,
  "order_lines": [
    { "product_id": 101, "quantity": 1, "price_unit": 3.5 }
  ]
}
```

Telegram order (`POST /telegram/order`) JSON only
```json
{
  "partner_id": 1,
  "shop_id": 1,
  "telegram_id": 123456789,
  "notes": "Deliver to front desk",
  "lines": [
    {
      "template_id": 55,
      "qty": 2,
      "variant_value_ids": [11, 12],
      "price_unit": 4.0,
      "note": "Less ice",
      "addons": [
        { "product_id": 77, "qty": 1, "price_unit": 1.5, "note": "Extra shot" }
      ]
    }
  ]
}
```

## 5) Key Behavioral Findings & Security Concerns (Deep Review)

1. **Inconsistent Payload Styles**: Payload style varies drastically by endpoint. Some endpoints (e.g. `variant_update`) accept JSON and form data, while closely related endpoints (e.g. `variant_create`, `variant_value_update`) only accept form data.
2. **Inconsistent Error Schema**: Error schema is inconsistent (`{'error': '...'}` vs `{"status": "error", "message": "...", "errors": [...]}`), making client-side error handling non-uniform.
3. **`POST /refresh` Content Type Strictness**: The endpoint hard-requires `Content-Type: application/json` even though it still contains logic to parse a form fallback.
4. **Variant Endpoint Discrepancies**: `POST /shop/{shop_id}/product/variant` is form-only, while update/patch for the same resource supports JSON and form.
5. **Field Name Mismatches**: `PUT/PATCH /shop/{shop_id}/product/variant/value/{value_id}` expects `price_extra` in the payload, but list responses expose it as `extra_price`.
6. **Path Parameter Misnomer**: `GET /shop/{shop_id}/product/{variant_id}/value` uses `variant_id` in path but actually targets a product attribute ID.
7. **Overlapping Shop Creation Routes**: `POST /shop` and `POST /shop/create` overlap functionality with different payload handling. `POST /shop/create` also automatically changes the user's `partner_id.parent_id` to the new shop, which `POST /shop` does not do.
8. **Silent Filter Ignorance**: Most list endpoints silently ignore invalid filters/sort parameters instead of returning explicit validation errors.
9. **`cart/checkout` JSON-RPC**: The `cart/checkout` route uses `type="json"`, so client integration must treat it as a JSON-RPC format, unlike the rest of the HTTP REST API.
10. **CRITICAL SECURITY FLAW - `GET /sale`**: The global sale order route (`GET /sale`) has `auth="public"` and uses `.sudo()`. This exposes **all** sale orders globally to unauthenticated users, leading to a massive data leak.
11. **HIGH PRIVILEGE ROUTE - `POST /telegram/order`**: This route runs with `uid=2` (`sudo`) by design with `auth="public"`. This allows an unauthenticated user to create orders on behalf of any customer as long as they provide a valid `partner_id`. This should be heavily guarded in production (e.g., via IP whitelisting or a secret webhook token).

## 6) Generated Postman File

Import this file into Postman:
- `/Users/khanvuthy/Documents/odoo/odoo18-project/angkort/e_menu/controllers/api/Angkort_Shop_API_Postman_Collection_Deep_Review.json`

Highlights of generated collection:
- Includes existing full endpoint set from current project collection.
- Adds explicit form examples for login/register and `/shop/create`.
- Adds explicit JSON example for variant PUT and form example for variant PATCH.
- Keeps variables for fast testing (`base_url`, `api_prefix`, `shop_id`, `variant_id`, etc.).
