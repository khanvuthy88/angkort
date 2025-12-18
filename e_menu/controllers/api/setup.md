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
  "partner_id": 12,       // Integer: ID of the Odoo partner (customer)
  "order_lines": [
    {
      "product_id": 5,    // Integer: ID of the product (template or variant)
      "quantity": 2,      // Float: Quantity to order
      "price_unit": 10.5  // Float: (Optional) Unit price override
    },
    {
      "product_id": 8,
      "quantity": 1
    }
  ]
}
```

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
    partner_id: 10, // Replace with actual selected customer ID
    order_lines: [
        { product_id: 5, quantity: 2 },
        { product_id: 8, quantity: 1 }
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

*   **401 Unauthorized - Missing X-Telegram-Init-Data header**: Ensure you are passing the header correctly.
*   **401 Unauthorized - Invalid Telegram data**: verify that your Odoo System Parameter `angkort.telegram_bot_token` matches the bot token of the Mini App you are using. Also, ensure `initData` is not stale (older than 24 hours).
*   **500 Internal Server Error - Telegram Bot Token not configured**: You missed Step 1 (Odoo Configuration).