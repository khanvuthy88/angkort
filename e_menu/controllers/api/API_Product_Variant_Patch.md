# Partially Update Product Variant (PATCH)

Partially update an existing product variant (attribute) for a specific shop. Only sent fields are updated.

---

## Endpoint

```
PATCH /angkort/api/v1/shop/{shop_id}/product/variant/{variant_id}
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
| `Content-Type`    | string | Yes      | `application/json` **or** `application/x-www-form-urlencoded` / `multipart/form-data`. |
| `Authorization`   | string | Yes      | Bearer token or app auth.      |

### Body

**Accepted formats:**

- **JSON:** `Content-Type: application/json` — body is a JSON object.
- **Form:** `Content-Type: application/x-www-form-urlencoded` or `multipart/form-data` — body is form fields.

Only these fields are accepted; any other keys are ignored. **At least one** of these fields must be present and valid, or the request returns 400.

| Field            | Type   | Required | Description |
|------------------|--------|----------|-------------|
| `name`           | string | No       | Display name of the variant. Must be unique per shop. If same as current, it is not updated. |
| `create_variant` | string | No       | When to create product variants. Enum: `"no_variant"` \| `"always"`. |
| `display_type`   | string | No       | How options are shown. Enum: `"multi"` \| `"radio"`. If `"multi"`, `create_variant` is set to `"no_variant"`. |

**Validation rules:**

- `create_variant`: if present, must be one of `no_variant`, `always`.
- `display_type`: if present, must be one of `multi`, `radio`.
- `name`: if provided and different from current, must not already exist for this shop (empty/whitespace is ignored).
- At least one valid field must be provided; otherwise 400 "No valid fields provided for update".

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

### 400 Bad Request – No valid fields

Sent when body is empty or contains no valid/updatable fields.

```json
{
  "status": "error",
  "message": "Failed to patch variant",
  "statusCode": "400",
  "errors": [
    {
      "name": "general",
      "message": "No valid fields provided for update"
    }
  ]
}
```

### 400 Bad Request – Invalid `create_variant`

```json
{
  "status": "error",
  "message": "Failed to patch variant",
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
  "message": "Failed to patch variant",
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
  "message": "Failed to patch variant",
  "statusCode": "400",
  "errors": [
    {
      "name": "name",
      "message": "Attribute with name 'Size' already exists"
    }
  ]
}
```

### 404 Not Found – Shop not found

```json
{
  "status": "error",
  "message": "Failed to patch variant",
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
  "message": "Failed to patch variant",
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
  "message": "Failed to patch variant",
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

// Request body (JSON or form) – at least one field required
body: {
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

### cURL – JSON body (update name only)

```bash
curl -X PATCH "https://your-odoo.com/angkort/api/v1/shop/1/product/variant/5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name": "Size"}'
```

### cURL – JSON body (update display_type and create_variant)

```bash
curl -X PATCH "https://your-odoo.com/angkort/api/v1/shop/1/product/variant/5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"display_type": "radio", "create_variant": "always"}'
```

### cURL – Form body

```bash
curl -X PATCH "https://your-odoo.com/angkort/api/v1/shop/1/product/variant/5" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "name=Color" \
  -d "display_type=multi"
```

### JavaScript (fetch, JSON)

```javascript
const shopId = 1;
const variantId = 5;

const response = await fetch(
  `https://your-odoo.com/angkort/api/v1/shop/${shopId}/product/variant/${variantId}`,
  {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer YOUR_TOKEN',
    },
    body: JSON.stringify({ name: 'Size', display_type: 'radio' }),
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

1. **JSON or form:** PATCH accepts either `application/json` or form-encoded body; PUT in this API is form-only.
2. **Partial update:** Only fields present in the body are validated and written; others are unchanged.
3. **At least one field:** Sending an empty body or no valid field returns 400 "No valid fields provided for update".
4. **display_type = multi:** When `display_type` is `multi`, `create_variant` is set to `no_variant` automatically.
5. **Allowed fields:** Only `name`, `create_variant`, and `display_type` are accepted; other keys are ignored.
6. **Variant scope:** The attribute must belong to the given `shop_id`; otherwise the response is 404 "Attribute not found".
