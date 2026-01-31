# Angkort Shop API — Request Body / Payload Reference

Base URL: `/angkort/api/v1`

This document details **request body and payload** for all endpoints that accept POST, PUT, or PATCH. GET endpoints use **query parameters** only (summarized at the end).

---

## Authentication

- **Public:** No `Authorization` header.
- **angkit:** Send `Authorization: Bearer <access_token>` (from login/register/refresh).
- **Ownership:** Some endpoints require the authenticated user to own the resource (shop, variant, wifi, etc.).

---

## 1. Auth

### 1.1 POST `/angkort/api/v1/login`

**Content-Type:** `application/json`

| Field      | Type   | Required | Description        |
|-----------|--------|----------|--------------------|
| `username`| string | Yes      | User login         |
| `password`| string | Yes      | User password      |

**Sample body:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

---

### 1.2 POST `/angkort/api/v1/register`

**Content-Type:** `application/json`

| Field      | Type   | Required | Description        |
|-----------|--------|----------|--------------------|
| `name`   | string | Yes      | Display name       |
| `username`| string | Yes      | Login (unique)     |
| `password`| string | Yes      | Password           |

**Sample body:**
```json
{
  "name": "John Doe",
  "username": "johndoe",
  "password": "securePassword123"
}
```

---

### 1.3 POST `/angkort/api/v1/refresh`

**Content-Type:** `application/json` (required)

| Field           | Type   | Required | Description     |
|----------------|--------|----------|-----------------|
| `refresh_token`| string | Yes      | Refresh token   |

**Sample body:**
```json
{
  "refresh_token": "YOUR_REFRESH_TOKEN_HERE"
}
```

---

### 1.4 POST `/angkort/api/v1/logout`

**Body:** None.  
**Headers:** `Authorization: Bearer <access_token>` required.

---

## 2. Shop

### 2.1 POST `/angkort/api/v1/shop` — Create shop (form)

**Content-Type:** `multipart/form-data` or `application/x-www-form-urlencoded`

**Required:**

| Field              | Type   | Required | Description          |
|--------------------|--------|----------|----------------------|
| `name`             | string | Yes      | Shop name            |
| `phone`            | string | Yes      | Phone number         |
| `customer_address`  | string | Yes      | Shop address         |

**Optional (from PARTNER_FIELDS):**

| Field              | Type   | Description                    |
|--------------------|--------|--------------------------------|
| `wifi_name`        | string | WiFi name(s)                   |
| `phone`            | string | (already required)              |
| `email`            | string | Email                          |
| `shop_latitude`    | number | Latitude                       |
| `shop_longitude`   | number | Longitude                      |
| `shop_banner`      | file   | Banner image (form file)       |
| `shop_wifi_ids`    | string | JSON array of `{ name, password }` |
| `shop_open_hour_ids`| string | JSON array of `{ day, open, close }` (day: "0"-"6") |

**Sample form data (key-value):**
- `name`: My Coffee Shop  
- `phone`: +85512345678  
- `customer_address`: 123 Street, Phnom Penh  
- `shop_wifi_ids`: `[{"name":"GuestWifi","password":"wifi123"}]`  
- `shop_open_hour_ids`: `[{"day":"0","open":"08:00","close":"22:00"}]`  
- `shop_banner`: (file)

---

### 2.2 POST `/angkort/api/v1/shop/create` — Create shop (JSON)

**Content-Type:** `application/json`

**Required:**

| Field              | Type   | Required | Description          |
|--------------------|--------|----------|----------------------|
| `name`             | string | Yes      | Shop name            |
| `phone`            | string | Yes      | Phone number         |
| `customer_address`  | string | Yes      | Shop address         |

**Optional:**

| Field              | Type   | Description          |
|--------------------|--------|----------------------|
| `wifi_name`        | string | Default ""           |
| `shop_latitude`    | number | Default 0.0          |
| `shop_longitude`   | number | Default 0.0          |
| `email`            | string | Default ""           |

**Sample body:**
```json
{
  "name": "My Coffee Shop",
  "phone": "+85512345678",
  "customer_address": "123 Street, Phnom Penh",
  "wifi_name": "",
  "shop_latitude": 0.0,
  "shop_longitude": 0.0,
  "email": "shop@example.com"
}
```
Body may also be wrapped in `params`: `{ "params": { ... } }`.

---

### 2.3 PUT `/angkort/api/v1/shop/<shop_id>` — Update shop

**Content-Type:** form (and optional file for banner)

**Body:** Same allowed fields as shop create (form). Only provided fields are updated.  
- `shop_wifi_ids`: JSON string, e.g. `[{"name":"Wifi1","password":"pass1"}]` — **replaces** all existing WiFi.  
- `shop_open_hour_ids`: JSON string, e.g. `[{"day":"0","open":"08:00","close":"22:00"}]` — **replaces** all open hours.  
- `shop_banner`: file (optional).

**Sample form:**
- `name`: Updated Shop Name  
- `phone`: +85598765432  
- `customer_address`: New Address  
- `shop_wifi_ids`: `[{"name":"Wifi1","password":"pass1"}]`  
- `shop_open_hour_ids`: `[{"day":"0","open":"08:00","close":"22:00"}]`

---

### 2.4 PATCH `/angkort/api/v1/shop/<shop_id>` — Partial update shop

**Content-Type:** form (and optional file)

**Body:** Any subset of PARTNER_FIELDS and shop-related fields (banner, shop_wifi_ids, shop_open_hour_ids). Only sent fields are updated. Same structure as PUT.

---

### 2.5 POST `/angkort/api/v1/shop/<shop_id>/wifi` — Create WiFi

**Content-Type:** form (optional file for QR)

| Field           | Type | Required | Description      |
|----------------|------|----------|------------------|
| `name`         | string | Yes    | WiFi name        |
| `password`     | string | Yes    | WiFi password    |
| `wifi_qr_code` | file  | No      | QR image file    |

**Sample:** `name`: GuestWifi, `password`: wifi123, `wifi_qr_code`: (file)

---

### 2.6 PUT `/angkort/api/v1/shop/<shop_id>/wifi/<wifi_id>` — Update WiFi

**Content-Type:** form

**Body:** Any of `name`, `password`, `wifi_qr_code` (file). At least one required for update.

---

### 2.7 POST `/angkort/api/v1/shop/<shop_id>/banner` — Update banner

**Content-Type:** `multipart/form-data`

| Field         | Type | Required | Description   |
|---------------|------|----------|---------------|
| `shop_banner` | file | Yes      | Banner image  |

---

### 2.8 POST `/angkort/api/v1/shop/<shop_id>/open-hours` — Create open hour

**Content-Type:** form

| Field  | Type   | Required | Description                          |
|--------|--------|----------|--------------------------------------|
| `day`  | string | Yes      | "0"=Monday … "6"=Sunday              |
| `open` | string | Yes      | Opening time (e.g. "08:00")         |
| `close`| string | Yes      | Closing time (e.g. "22:00")         |

**Sample:** `day`: 0, `open`: 08:00, `close`: 22:00

---

### 2.9 PUT `/angkort/api/v1/shop/<shop_id>/open-hours/<hour_id>` — Update open hour

**Content-Type:** form

**Body:** Any of `day`, `open`, `close`. At least one required. Same validation as create (day 0–6, no duplicate day per shop).

---

## 3. Product / Variant / Value

### 3.1 POST `/angkort/api/v1/shop/<shop_id>/product/variant` — Create variant (attribute)

**Content-Type:** form

| Field            | Type   | Required | Description                              |
|------------------|--------|----------|------------------------------------------|
| `name`           | string | Yes      | Attribute name (e.g. "Size")            |
| `create_variant` | string | Yes      | `"no_variant"` or `"always"`             |
| `display_type`   | string | Yes      | `"multi"` or `"radio"`                   |

If `display_type` is `"multi"`, backend sets `create_variant` to `"no_variant"`. Name must be unique per shop.

**Sample:** `name`: Size, `create_variant`: always, `display_type`: radio

---

### 3.2 PUT `/angkort/api/v1/shop/<shop_id>/product/variant/<variant_id>` — Update variant

**Content-Type:** form

**Body:** Same fields as create: `name`, `create_variant`, `display_type`. All sent fields are updated.

---

### 3.3 PATCH `/angkort/api/v1/shop/<shop_id>/product/variant/<variant_id>` — Partial update variant

**Content-Type:** `application/json` **or** form

**Body:** Any subset of:

| Field            | Type   | Required | Description                    |
|------------------|--------|----------|--------------------------------|
| `name`           | string | No       | Unique per shop               |
| `create_variant`| string | No       | `no_variant` \| `always`       |
| `display_type`   | string | No       | `multi` \| `radio`            |

At least one valid field must be present.

**Sample JSON:**
```json
{
  "name": "Size",
  "create_variant": "no_variant",
  "display_type": "radio"
}
```

---

### 3.4 POST `/angkort/api/v1/shop/<shop_id>/product/variant/value` — Create variant values

**Content-Type:** form

| Field           | Type   | Required | Description                                      |
|-----------------|--------|----------|--------------------------------------------------|
| `attribute_id`  | number | Yes      | Attribute (variant) ID                           |
| `values`        | string | Yes      | JSON array of `{ "name": string, "extra_price"?: number }` |

**Sample form:**
- `attribute_id`: 1  
- `values`: `[{"name":"Small","extra_price":0},{"name":"Large","extra_price":1.5}]`

---

### 3.5 PUT `/angkort/api/v1/shop/<shop_id>/product/variant/value/<value_id>` — Update variant value

**Content-Type:** form

| Field         | Type   | Required | Description (stored as default_extra_price) |
|---------------|--------|----------|---------------------------------------------|
| `name`        | string | No       | Value name                                  |
| `price_extra` | number | No       | Extra price                                 |

At least one of `name` or `price_extra` required.

---

### 3.6 PATCH `/angkort/api/v1/shop/<shop_id>/product/variant/value/<value_id>` — Partial update variant value

**Content-Type:** form

**Body:** Same as PUT — any of `name`, `price_extra`. At least one required.

---

### 3.7 POST `/angkort/api/v1/image/add` — Upload image

**Content-Type:** `multipart/form-data`

| Field       | Type | Required | Description           |
|-------------|------|----------|-----------------------|
| `image`     | file | Yes      | Image file            |
| `res_id`    | any  | No       | Resource ID (default 0) |
| `res_model` | string | No     | Resource model (default "ir.ui.view") |

**Sample:** `image`: (file), `res_model`: ir.ui.view, `res_id`: 0

---

## 4. Order

### 4.1 POST `/angkort/api/v1/my/order` — Create my order

**Content-Type:** `application/json`

| Field         | Type  | Required | Description                                  |
|---------------|-------|----------|----------------------------------------------|
| `order_lines` | array | Yes      | List of `{ product_id, quantity, price_unit? }` |
| `note`        | string| No       | Order note                                   |

- `product_id`: template ID or variant ID (backend resolves variant).  
- `quantity`: number > 0.  
- `price_unit`: optional; if omitted, uses product list price.

**Sample body:**
```json
{
  "order_lines": [
    { "product_id": 1, "quantity": 2, "price_unit": 3.50 },
    { "product_id": 2, "quantity": 1 }
  ],
  "note": "No onions"
}
```

---

### 4.2 POST `/angkort/api/v1/cart/checkout` — Cart validation

**Content-Type:** `application/json`  
**Route type:** Odoo `type="json"` (JSON-RPC); client often sends JSON body.

| Field  | Type  | Required | Description                        |
|--------|-------|----------|------------------------------------|
| `cart` | array | Yes      | List of `{ product_id, quantity }` |

**Sample body:**
```json
{
  "cart": [
    { "product_id": 1, "quantity": 2 },
    { "product_id": 2, "quantity": 1 }
  ]
}
```

Response indicates `sufficient_stock` / `insufficient_stock` and `total_amount`.

---

### 4.3 POST `/angkort/api/v1/order` — Global order create

**Content-Type:** `application/json`

| Field         | Type  | Required | Description                                    |
|---------------|-------|----------|------------------------------------------------|
| `partner_id`  | number| Yes      | Customer (res.partner) ID                      |
| `order_lines` | array | Yes      | List of `{ product_id, quantity, price_unit? }` |

`product_id` here is **product.product** (variant) ID.

**Sample body:**
```json
{
  "partner_id": 1,
  "order_lines": [
    { "product_id": 1, "quantity": 2, "price_unit": 3.50 },
    { "product_id": 2, "quantity": 1, "price_unit": 0.0 }
  ]
}
```

---

### 4.4 POST `/angkort/api/v1/telegram/order` — Telegram order create

**Content-Type:** `application/json`  
**Auth:** Public (runs as internal user ID 2).

| Field         | Type   | Required | Description |
|---------------|--------|----------|-------------|
| `partner_id`  | number | Yes      | Customer (res.partner) ID |
| `lines`       | array  | Yes      | Order line items (see below) |
| `shop_id`     | number | No       | Shop (store) partner ID |
| `telegram_id` | number | No       | Client Telegram ID for notifications |
| `order_date`  | string | No       | ISO date/time (e.g. "2025-12-28T10:00:00Z") |
| `notes`       | string | No       | Order note |

**Line item object:**

| Field              | Type   | Required | Description |
|--------------------|--------|----------|-------------|
| `template_id`      | number | Yes*     | Product template ID |
| `product_id` / `variant_id` | number | Yes* | Variant ID (alternative to template_id) |
| `qty` / `quantity` | number | Yes      | Quantity |
| `variant_value_ids`| array  | No       | Attribute value IDs (for Size + options) |
| `price_unit`       | number | No       | Price override |
| `note`             | string | No       | Line note |
| `addons`           | array  | No       | Addon items (see below) |

*One of `template_id` or `product_id`/`variant_id` required.

**Addon object (inside `addons`):**

| Field        | Type   | Required | Description   |
|-------------|--------|----------|---------------|
| `product_id`| number | Yes      | Variant ID    |
| `qty` / `quantity` | number | Yes | Quantity   |
| `price_unit`| number | No       | Price override |
| `note`      | string | No       | Addon note   |

**Sample body:**
```json
{
  "partner_id": 1,
  "shop_id": 1,
  "telegram_id": 123456789,
  "order_date": "2025-12-28T10:00:00Z",
  "notes": "Delivery to front desk",
  "lines": [
    {
      "template_id": 1,
      "qty": 2,
      "variant_value_ids": [1, 2],
      "price_unit": 4.00,
      "note": "Less ice",
      "addons": [
        { "product_id": 10, "qty": 1, "price_unit": 1.50, "note": "Extra shot" }
      ]
    }
  ]
}
```

Backward compatibility: `order_lines` may be accepted as alias for `lines`.

---

## 5. GET endpoints — Query parameters summary

| Endpoint | Main query params |
|----------|--------------------|
| `GET /shop` | `page`, `limit`, `search`, `sort` (id\|name\|create_date), `order` (asc\|desc), `filter_industry`, `filter_has_wifi` (true\|false) |
| `GET /shop/<shop_id>` | — |
| `GET /shop/<shop_id>/product` | `page`, `limit`, `search`, `sort`, `order`, `filter_category`, `filter_price_min`, `filter_price_max`, `filter_has_variants` |
| `GET /product` | Same as above + `filter_shop` |
| `GET /product/<product_id>` | — |
| `GET /product/category` | `page`, `limit`, `search`, `sort`, `order`, `filter_parent`, `filter_has_children` |
| `GET /product/variant` | `page`, `limit`, `search`, `sort`, `order`, `filter_create_variant`, `filter_display_type` |
| `GET /shop/<shop_id>/product/variant` | `search`, `sort`, `order`, `filter_create_variant`, `filter_display_type` |
| `GET /shop/<shop_id>/product/<variant_id>/value` | `search`, `sort` (id\|name\|default_extra_price\|create_date), `order` |
| `GET /my/order` | `page`, `limit`, `search`, `order_by` (id\|name\|date_order), `order_direction` (asc\|desc) |
| `GET /my/order/<order_id>` | — |
| `GET /sale` | `page`, `limit`, `search`, `sort`, `order`, `filter_state`, `filter_date_from`, `filter_date_to`, `filter_amount_min`, `filter_amount_max`, `filter_customer` |

**Pagination:** `page` (default 1), `limit` (default 20, max 100).

---

## File reference

- **Postman collection:** `Angkort_Shop_API_Postman_Collection.json` — import into Postman for all requests and sample payloads.
- **Variant PATCH details:** `API_Product_Variant_Patch.md`
- **Variant Update details:** `API_Product_Variant_Update.md`
