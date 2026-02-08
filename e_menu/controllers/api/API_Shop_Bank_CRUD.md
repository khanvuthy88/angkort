# Shop Bank Accounts API (CRUD)

Base URL: `/angkort/api/v1`

Auth: `Authorization: Bearer <access_token>` (auth type `angkit`)

Content types:
- `application/json` for JSON requests
- `multipart/form-data` for file uploads (logo)

---

## List banks

`GET /shop/<shop_id>/bank`

Returns all banks for the shop ordered by `sequence, id`.

Example request:
```
GET /angkort/api/v1/shop/12/bank
Authorization: Bearer <token>
```

Example response (200):
```
[
  {
    "id": 3,
    "name": "ABA Bank",
    "code": "ABA",
    "link": "https://aba.com.kh/qr/123",
    "currency": "KHR",
    "logo": "https://example.com/web/image/angkort.shop.bank/3/logo",
    "active": true,
    "sequence": 10,
    "shop_id": 12
  },
  {
    "id": 4,
    "name": "Wing",
    "code": "WING",
    "link": "",
    "currency": "USD",
    "logo": "",
    "active": true,
    "sequence": 20,
    "shop_id": 12
  }
]
```

---

## Get bank detail

`GET /shop/<shop_id>/bank/<bank_id>`

Example request:
```
GET /angkort/api/v1/shop/12/bank/3
Authorization: Bearer <token>
```

Example response (200):
```
{
  "id": 3,
  "name": "ABA Bank",
  "code": "ABA",
  "link": "https://aba.com.kh/qr/123",
  "currency": "KHR",
  "logo": "https://example.com/web/image/angkort.shop.bank/3/logo",
  "active": true,
  "sequence": 10,
  "shop_id": 12
}
```

Example response (404):
```
{
  "status": "error",
  "message": "Failed to fetch bank",
  "statusCode": "404",
  "errors": [{"name": "bank_id", "message": "Bank not found"}]
}
```

---

## Create bank

`POST /shop/<shop_id>/bank`

Required fields: `name`, `code`, `currency` (KHR or USD)  
Optional fields: `link`, `sequence`, `active`, `logo`

### JSON example
```
POST /angkort/api/v1/shop/12/bank
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ABA Bank",
  "code": "ABA",
  "currency": "KHR",
  "link": "https://aba.com.kh/qr/123",
  "sequence": 10,
  "active": true,
  "logo": "<base64>"
}
```

### multipart/form-data example (logo upload)
```
POST /angkort/api/v1/shop/12/bank
Authorization: Bearer <token>
Content-Type: multipart/form-data

name=ABA Bank
code=ABA
currency=KHR
link=https://aba.com.kh/qr/123
sequence=10
active=true
logo=<file>
```

Example response (201):
```
{
  "id": 3,
  "name": "ABA Bank",
  "code": "ABA",
  "link": "https://aba.com.kh/qr/123",
  "currency": "KHR",
  "logo": "https://example.com/web/image/angkort.shop.bank/3/logo",
  "active": true,
  "sequence": 10,
  "shop_id": 12
}
```

Example response (400 - missing fields):
```
{
  "status": "error",
  "message": "Failed to create bank",
  "statusCode": "400",
  "errors": [{"name": "name", "message": "Name is required"}]
}
```

---

## Update bank

`PUT /shop/<shop_id>/bank/<bank_id>`

Updatable fields: `name`, `code`, `currency` (KHR or USD), `link`, `sequence`, `active`, `logo`

Example request:
```
PUT /angkort/api/v1/shop/12/bank/3
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ABA Bank (Updated)",
  "currency": "USD",
  "active": false,
  "sequence": 5
}
```

Example response (200):
```
{
  "id": 3,
  "name": "ABA Bank (Updated)",
  "code": "ABA",
  "link": "https://aba.com.kh/qr/123",
  "currency": "USD",
  "logo": "https://example.com/web/image/angkort.shop.bank/3/logo",
  "active": false,
  "sequence": 5,
  "shop_id": 12
}
```

Example response (400 - no fields):
```
{
  "status": "error",
  "message": "Failed to update bank",
  "statusCode": "400",
  "errors": [{"name": "fields", "message": "No valid fields to update"}]
}
```

---

## Delete bank

`DELETE /shop/<shop_id>/bank/<bank_id>`

Example request:
```
DELETE /angkort/api/v1/shop/12/bank/3
Authorization: Bearer <token>
```

Example response (204): No content
