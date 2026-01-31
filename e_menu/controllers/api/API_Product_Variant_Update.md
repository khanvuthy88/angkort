# Update Product Variant (PUT)

Update an existing product variant (attribute) for a specific shop.

---

## Endpoint

```
PUT /angkort/api/v1/shop/{shop_id}/product/variant/{variant_id}
```

| Segment      | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `shop_id`   | number | Shop ID (path parameter).            |
| `variant_id`| number | Product attribute (variant) ID (path). |

---

## Authentication

- **Auth:** `angkit` (token-based).
- **Ownership:** Caller must own the variant (enforced by `@verify_ownership(entity_type='variant')`).

---

## Request

### Headers

| Header            | Type   | Required | Description                    |
|-------------------|--------|----------|--------------------------------|
| `Content-Type`    | string | Yes      | `application/x-www-form-urlencoded` or `multipart/form-data`. |
| `Authorization`   | string | Yes      | Bearer token or app auth.      |

### Body (form fields)

All body fields are optional; only sent fields are updated.

| Field            | Type   | Required | Description |
|------------------|--------|----------|-------------|
| `name`           | string | No       | Display name of the variant. Must be unique per shop. |
| `create_variant` | string | No       | When to create product variants. Enum: `"no_variant"` \| `"always"`. |
| `display_type`   | string | No       | How options are shown. Enum: `"multi"` \| `"radio"`. If `"multi"`, `create_variant` is forced to `"no_variant"`. |

**Validation rules:**

- `create_variant`: must be one of `no_variant`, `always`.
- `display_type`: must be one of `multi`, `radio`.
- `name`: if provided and different from current, must not already exist for this shop.

---

## Response

### Success (200 OK)

**Content-Type:** `application/json`

**Body:** Updated variant object (attribute).

| Field          | Type   | Description                    |
|----------------|--------|--------------------------------|
| `id`           | number | Attribute ID.                 |
| `name`         | string | Attribute name.               |
| `create_variant` | string | `"no_variant"` or `"always"`. |
| `display_type` | string | `"multi"` or `"radio"`.       |

---

## Error responses

### 400 Bad Request – Invalid `create_variant`

```json
{
  "status": "error",
  "message": "Failed to update variant",
  "statusCode": "400",
  "errors": [
    {
      "name": "create_variant",
      "message": "Invalid create_variant value. Must be one of: no_variant, always"
    }
  ]
}
```

### 400 Bad Request – Invalid `display_type`

```json
{
  "status": "error",
  "message": "Failed to update variant",
  "statusCode": "400",
  "errors": [
    {
      "name": "display_type",
      "message": "Invalid display_type value. Must be one of: multi, radio"
    }
  ]
}
```

### 400 Bad Request – Duplicate variant name

```json
{
  "status": "error",
  "message": "Failed to update variant",
  "statusCode": "400",
  "errors": [
    {
      "name": "name",
      "message": "Attribute with name Size already exists"
    }
  ]
}
```

### 404 Not Found – Shop not found

```json
{
  "status": "error",
  "message": "Failed to update variant",
  "statusCode": "404",
  "errors": [
    {
      "name": "shop_id",
      "message": "Shop not found"
    }
  ]
}
```

### 404 Not Found – Variant (attribute) not found

```json
{
  "status": "error",
  "message": "Failed to update variant",
  "statusCode": "404",
  "errors": [
    {
      "name": "variant_id",
      "message": "Attribute not found"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "status": "error",
  "message": "Failed to update variant",
  "statusCode": "500",
  "errors": [
    {
      "name": "general",
      "message": "<error details>"
    }
  ]
}
```

---

## Type summary

```ts
// Path params
shop_id: number;
variant_id: number;

// Request body (form)
body?: {
  name?: string;
  create_variant?: 'no_variant' | 'always';
  display_type?: 'multi' | 'radio';
};

// Success response (200)
{
  id: number;
  name: string;
  create_variant: 'no_variant' | 'always';
  display_type: 'multi' | 'radio';
}

// Error response (4xx/5xx)
{
  status: 'error';
  message: string;
  statusCode: number;
  errors: Array<{ name: string; message: string }>;
}
```

---

## Examples

### cURL – Update name and display type

```bash
curl -X PUT "https://your-odoo.com/angkort/api/v1/shop/1/product/variant/5" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "name=Size" \
  -d "display_type=radio" \
  -d "create_variant=always"
```

### cURL – Update only name

```bash
curl -X PUT "https://your-odoo.com/angkort/api/v1/shop/1/product/variant/5" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "name=Color"
```

### JavaScript (fetch)

```javascript
const shopId = 1;
const variantId = 5;

const form = new URLSearchParams();
form.append('name', 'Size');
form.append('display_type', 'radio');
form.append('create_variant', 'always');

const response = await fetch(
  `https://your-odoo.com/angkort/api/v1/shop/${shopId}/product/variant/${variantId}`,
  {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': 'Bearer YOUR_TOKEN',
    },
    body: form.toString(),
  }
);

const data = await response.json();
// 200: { id: 5, name: "Size", create_variant: "always", display_type: "radio" }
```

### Example success response (200)

```json
{
  "id": 5,
  "name": "Size",
  "create_variant": "always",
  "display_type": "radio"
}
```

---

## Notes

1. **Form data only:** Request body must be form-encoded; JSON body is not used for this route.
2. **Partial update:** Omitted fields are left unchanged.
3. **display_type = multi:** When `display_type` is sent as `multi`, the API sets `create_variant` to `no_variant` before saving.
4. **Variant scope:** The attribute must belong to the given `shop_id`; otherwise the response is 404 “Attribute not found”.
