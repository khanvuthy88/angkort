# Telegram Order API Setup

This guide explains how to configure and use the `/angkort/api/v1/telegram/order` endpoint for your Telegram Mini App.

## 1. Odoo Configuration

Before using the endpoint, you must configure your Telegram Bot Token in Odoo. This token is used to verify the integrity of requests coming from Telegram.

1.  Log in to Odoo as an Administrator.
2.  Enable **Developer Mode** (Settings > Scroll down > Activate Developer Mode).
3.  Go to **Settings > Technical > Parameters > System Parameters**.
4.  Click **Create**.
5.  Enter the following details:
    *   **Key**: `angkort.telegram_bot_token`
    *   **Value**: `YOUR_TELEGRAM_BOT_TOKEN` (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyZ`)
6.  Save the record.

## 2. Endpoint Details

*   **URL**: `/angkort/api/v1/telegram/order`
*   **Method**: `POST`
*   **Auth**: Public (Secured via `X-Telegram-Init-Data` header)

## 3. Request Structure

### Headers

| Header | Required | Description |
| :--- | :--- | :--- |
| `Content-Type` | Yes | Must be `application/json` |
| `X-Telegram-Init-Data` | Yes | The raw `initData` string from Telegram WebApp SDK (`window.Telegram.WebApp.initData`). |

#### Sample X-Telegram-Init-Data Value
```text
query_id=AAH4_v...&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22John%22%2C%22last_name%22%3A%22Doe%22%2C%22username%22%3A%22johndoe%22%2C%22language_code%22%3A%22en%22%7D&auth_date=1686641237&hash=2d1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

### Body (JSON)

```json
{
  "partner_id": 63,                    // Integer (Required): ID of the Odoo partner (customer)
  "shop_id": 62,                       // Integer (Optional): ID of the shop/store partner (type='store')
  "order_date": "2025-12-28T10:00:00Z", // String (Optional): ISO format date string
  "notes": "Customer prefers quick delivery", // String (Optional): Order-level note
  "lines": [                           // Array (Required): Order line items
    {
      "template_id": 51,               // Integer (Required): Product template ID
      "qty": 1,                        // Float (Required): Quantity
      "variant_value_ids": [20, 27],   // Array[Integer] (Optional): Attribute value IDs (Size + Extra Options)
      "price_unit": 17.95,             // Float (Optional): Price override per unit
      "note": "Size M with Protection kit", // String (Optional): Line-level note
      "addons": [                      // Array (Optional): Separate products (e.g., drinks)
        {
          "product_id": 92,            // Integer (Required): Product variant ID
          "qty": 1,                    // Float (Required): Quantity
          "price_unit": 1.22,          // Float (Optional): Price override
          "note": "Extra drink"        // String (Optional): Addon note
        }
      ]
    },
    {
      "template_id": 51,
      "qty": 2,
      "variant_value_ids": [21],       // Size L
      "price_unit": 3.45,
      "note": "Size L"
    },
    {
      "template_id": 52,
      "qty": 1,
      "price_unit": 6.1,
      "note": "No special instructions"
    }
  ]
}
```

**Field Notes:**

- `partner_id` → Odoo customer (res.partner) ID (Required)
- `shop_id` → Shop/store partner ID (Optional, must be type='store')
- `order_date` → ISO format date string, e.g., "2025-12-28T10:00:00Z" (Optional)
- `notes` → Order-level note string (Optional)
- `lines` → Array of order line items (Required)
  - `template_id` → Product template ID (Required)
  - `qty` → Quantity as float (Required)
  - `variant_value_ids` → Array of attribute value IDs for Size and Extra Options (Optional)
    - All attribute values (Size + Extra Options) are stored together in the same order line
    - Example: `[20, 27]` = Size M (20) + Protection kit (27)
  - `price_unit` → Optional unit price override (Optional)
  - `note` → Line-level note string (Optional)
  - `addons` → Array of separate products like drinks, sides (Optional)
    - Each addon creates a separate order line
    - Use `product_id` (variant ID), not template_id
    - Supports `qty`, `price_unit`, and `note`

**Important:** 
- Use `variant_value_ids` for Size and Extra Options (stored in the same line)
- Use `addons` array only for separate products that should be on different lines
- The API supports both `lines` (new) and `order_lines` (legacy) for backward compatibility
- The API supports both `qty` and `quantity` for backward compatibility

## 4. Frontend Implementation (JavaScript)

Use the following code snippet in your Telegram Mini App frontend to submit an order.

```javascript
// 1. Get the raw security data from Telegram SDK
const initData = window.Telegram.WebApp.initData;

if (!initData) {
    console.error("App is not running inside Telegram or initData is missing.");
    return;
}

// 2. Prepare the order payload
const payload = {
    partner_id: 63,  // Replace with actual customer ID
    shop_id: 62,     // Optional: Shop/store ID
    notes: "Customer prefers quick delivery",  // Optional: Order-level note
    lines: [
        {
            template_id: 51,                    // Product template ID
            qty: 1,                             // Quantity
            variant_value_ids: [20, 27],        // Size M (20) + Protection kit (27)
            price_unit: 17.95,                  // Optional: Price override
            note: "Size M with Protection kit", // Optional: Line note
            addons: [                           // Optional: Separate products
                {
                    product_id: 92,             // Product variant ID (not template_id)
                    qty: 1,
                    price_unit: 1.22,
                    note: "Extra drink"
                }
            ]
        },
        {
            template_id: 51,
            qty: 2,
            variant_value_ids: [21],            // Size L only
            note: "Size L"
        }
    ]
};

// 3. Send Request
async function submitOrder() {
    try {
        const response = await fetch('https://your-odoo-domain.com/angkort/api/v1/telegram/order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Init-Data': initData  // <--- Crucial for validation
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (response.ok && result.status) {
            window.Telegram.WebApp.showAlert(`Success! Order ${result.data.order_name} created.`);
        } else {
            console.error('API Error:', result);
            window.Telegram.WebApp.showAlert(`Error: ${result.error || result.message}`);
        }
    } catch (error) {
        console.error('Network Error:', error);
        window.Telegram.WebApp.showAlert("Failed to connect to server.");
    }
}
```

## 5. Troubleshooting

*   **400 Bad Request - Missing required field 'partner_id'**: Ensure `partner_id` is included in the request body.
*   **400 Bad Request - Missing required field 'lines'**: Ensure `lines` array is included and not empty.
*   **400 Bad Request - Partner not found**: Verify the `partner_id` exists in Odoo.
*   **400 Bad Request - No valid order lines created**: Check that `template_id` values exist and quantities are valid.
*   **401 Unauthorized - Missing X-Telegram-Init-Data header**: Ensure you are passing the header correctly.
*   **401 Unauthorized - Invalid Telegram data**: Verify that your Odoo System Parameter `angkort.telegram_bot_token` matches the bot token of the Mini App you are using. Also, ensure `initData` is not stale (older than 24 hours).
*   **500 Internal Server Error - Telegram Bot Token not configured**: You missed Step 1 (Odoo Configuration).

## 6. Product Variant Selection Guide

### Summary Table

| **Scenario** | **What to Send** | **Why?** |
| --- | --- | --- |
| **Simple Product** (no variants or options) | `template_id` only | Odoo will use the default variant |
| **Product with Size** (e.g., Fried Chicken - Size M) | `template_id` + `variant_value_ids: [20]` | Size is stored as a no-variant attribute value |
| **Product with Size + Extra Options** (e.g., Burger + Size M + Protection kit) | `template_id` + `variant_value_ids: [20, 27]` | All attribute values (Size + Extra Options) stored together in same order line |
| **Product with Addons** (e.g., Burger + Drink) | `template_id` + `addons: [{product_id: 92, qty: 1}]` | Addons are separate products that create separate order lines |

**Key Concepts:**

- `template_id` → Use for the **main product item**
- `variant_value_ids` → Use for **Size and Extra Options** (all stored in the same order line as no-variant attributes)
- `addons` → Use for **separate products** like drinks, sides (creates separate order lines)

**Example Attribute Value IDs** (for template_id=51 - Fried Chicken):
- Size: S=19, M=20, L=21
- Extra Options: Cleaning kit=26, Protection kit=27, 1 year warranty extension=25

**Example Usage:**
- Size M + Protection kit: `variant_value_ids: [20, 27]` → Creates **one** order line
- Size L + Cleaning kit + Protection kit: `variant_value_ids: [21, 26, 27]` → Creates **one** order line
- Burger + Drink (separate products): Use `addons: [{product_id: 92, qty: 1}]` → Creates **two** order lines