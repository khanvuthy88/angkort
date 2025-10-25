# KHQR Payment - Quick Start Guide

## What is KHQR?

KHQR (Cambodian QR Code) is Cambodia's national QR code payment standard powered by Bakong, the National Bank of Cambodia's payment system. It allows seamless digital payments across all major Cambodian banks.

## Prerequisites

1. **Module Dependencies** (Already configured)
   - `account` - Odoo Accounting
   - `l10n_kh` - Cambodia Localization
   - `account_qr_code_emv` - EMV QR Code

2. **Bank Account Setup**
   - Cambodian bank account with Bakong ID
   - Either Solo Merchant or Corporate Merchant account

## Setup Guide

### Step 1: Configure Your Bank Account

1. Navigate to **Accounting → Configuration → Bank Accounts**
2. Click **Create** or edit an existing account
3. Fill in the following:
   ```
   Account Holder: Your Company
   Bank: [Select your Cambodian bank]
   Account Number: [Your account number]
   Country: Cambodia (KH)
   
   KHQR Settings:
   ├─ Proxy Type: Bakong Account ID (Solo Merchant) OR 
   │              Bakong Account ID (Corporate Merchant)
   ├─ Proxy Value: yourname@yourbank (e.g., mycompany@aba)
   └─ Merchant ID: [Required for Corporate Merchant only]
   ```
4. Click **Save**

### Step 2: Create a Subscription with KHQR Payment

1. Navigate to **HR → Subscriptions → All Subscriptions**
2. Click **Create**
3. Fill in subscription details:
   ```
   User: [Select user]
   Plan: [Basic/Premium/Enterprise]
   Billing Cycle: [Monthly/Yearly]
   Payment Method: KHQR (Bakong) ← Select this
   ```
4. Click **Save**

### Step 3: Generate KHQR Payment

**Option A: Using the Wizard (Recommended)**
1. Click **Setup KHQR Payment** button
2. Select your bank account
3. Click **Generate QR Code**
4. QR code will be displayed
5. Click **Done** when finished

**Option B: Quick Generate**
1. Select bank account in the subscription form
2. Click **Quick Generate KHQR** button
3. QR code appears immediately

### Step 4: Customer Pays

Customer scans the QR code with any KHQR-compatible banking app:
- ABA Mobile
- ACLEDA Mobile
- Wing
- Prince Bank
- Canadia Bank
- And more...

### Step 5: Confirm Payment

Once payment is received:
1. Click **Mark as Paid** button
2. Subscription becomes active
3. Invoice is automatically reconciled

## Quick Reference

### Button Guide

| Button | When Visible | Purpose |
|--------|-------------|---------|
| **Setup KHQR Payment** | KHQR method selected, not paid | Launch payment wizard |
| **Quick Generate KHQR** | Bank account selected | Generate without wizard |
| **Generate Invoice** | No invoice exists | Create invoice |
| **Mark as Paid** | Payment pending | Confirm payment received |
| **Activate** | Pending/Trial status | Activate subscription |

### Field Guide

| Field | Description | Required |
|-------|-------------|----------|
| **Payment Method** | Select "KHQR (Bakong)" | Yes |
| **Bank Account** | Your Bakong-enabled account | Yes for KHQR |
| **QR Code Data** | Generated QR string | Auto-generated |
| **QR Code Image** | Scannable QR image | Auto-generated |
| **Invoice** | Related invoice | Auto-created |

## Example: Complete Flow

```
1. Create Subscription
   ├─ Select user: John Doe
   ├─ Plan: Premium Plan ($299)
   ├─ Billing: Monthly
   └─ Payment: KHQR (Bakong)

2. Setup Payment
   ├─ Click "Setup KHQR Payment"
   ├─ Select bank: ABA Bank Account
   └─ Click "Generate QR Code"

3. QR Code Generated ✓
   ├─ Amount: $299 USD
   ├─ Merchant: Your Company
   └─ Reference: SUB/2025/0001

4. Customer Scans & Pays
   ├─ Opens ABA Mobile app
   ├─ Scans QR code
   └─ Confirms payment

5. Confirm Payment
   ├─ Click "Mark as Paid"
   ├─ Subscription → Active ✓
   └─ Invoice → Paid ✓
```

## Supported Currencies

- **KHR** - Cambodian Riel
- **USD** - US Dollar

## Common Issues

### "Missing Bank Account"
**Solution:** Select a bank account with Bakong ID in the subscription form

### "Invalid Proxy Type"
**Solution:** Bank account must have proxy type set to "Bakong Account ID"

### "Missing Merchant City"
**Solution:** Add city to your company's address

### QR Code Not Showing
**Solution:** 
1. Check payment method is set to KHQR
2. Ensure payment status is "Pending"
3. Click "Generate KHQR" button

## API Usage (For Developers)

### Create Subscription with KHQR

```python
subscription = env['hr.subscription'].create({
    'user_id': user_id,
    'plan_id': 'premium',
    'billing_cycle': 'monthly',
    'payment_method': 'khqr',
    'partner_bank_id': bank_account_id,
})
```

### Generate QR Code

```python
subscription.action_generate_khqr()
```

### Get QR Code URL

```python
qr_url = subscription.qr_code_url
# Returns: https://yourdomain.com/web/image/hr.subscription/{id}/qr_code_image
```

### Mark as Paid

```python
subscription.action_mark_as_paid()
```

## Testing

Test with demo data:
```bash
# Install module with demo data
odoo-bin -d your_database -i angkot_recruitement --load-language=km_KH
```

Demo subscriptions include KHQR payment examples.

## Next Steps

1. **Configure Bank Accounts** - Add all your Bakong accounts
2. **Test Payment Flow** - Create test subscription and generate QR
3. **Train Users** - Show team how to generate and process KHQR payments
4. **Monitor Payments** - Use subscription dashboard to track payments

## Support

For detailed information, see:
- **KHQR_PAYMENT_IMPLEMENTATION.md** - Complete technical documentation
- **[Bakong Website](https://bakong.nbc.gov.kh)** - Official KHQR information

## Tips

💡 **Best Practices:**
- Set up multiple bank accounts for redundancy
- Test QR codes with different banking apps
- Keep merchant information up to date
- Monitor payment status regularly
- Enable auto-renewal for recurring subscriptions

🎯 **Pro Tips:**
- Use Corporate Merchant for better tracking
- Include subscription reference in QR code
- Generate invoices before QR codes for better records
- Use the wizard for first-time setup
- Use quick generate for repeat operations

---

**Ready to accept KHQR payments!** 🎉

