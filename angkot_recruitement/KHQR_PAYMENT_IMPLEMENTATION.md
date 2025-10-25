# KHQR Payment Implementation for Job Portal Subscriptions

## Overview

This document describes the KHQR (Cambodia's national QR code payment system) implementation for job portal subscriptions in the Angkot Recruitment module.

## Features

### 1. KHQR Payment Method
- Added KHQR as a payment method option alongside Credit Card, PayPal, Bank Transfer, and Cash
- Integration with Cambodia's Bakong payment system
- Support for both Solo Merchant and Corporate Merchant accounts

### 2. Invoice Generation
- Automatic invoice creation for subscriptions
- Link invoices to subscriptions for tracking
- Support for multiple currencies (KHR and USD)

### 3. QR Code Generation
- Generate EMV-compliant QR codes for payments
- Display QR codes directly in subscription form
- QR code includes payment amount, merchant info, and subscription reference

### 4. Payment Wizard
- User-friendly wizard for configuring KHQR payments
- Select bank account with Bakong ID
- Generate and display QR code for payment
- Support for multiple bank accounts

## Technical Implementation

### Dependencies
The implementation requires the following Odoo modules:
- `account` - Accounting and invoicing
- `l10n_kh` - Cambodia localization
- `account_qr_code_emv` - EMV QR code generation

### Models

#### 1. hr.subscription (Enhanced)

**New Fields:**
- `payment_method` - Added 'khqr' option
- `invoice_id` - Link to generated invoice
- `invoice_count` - Count of invoices (for stat button)
- `partner_bank_id` - Bank account for KHQR payment
- `qr_code_data` - EMV QR code data string
- `qr_code_image` - QR code image (binary)
- `qr_code_url` - URL to access QR code image
- `show_qr_code` - Computed field to show/hide QR code

**New Methods:**
- `action_view_invoice()` - View related invoice
- `action_generate_invoice()` - Generate invoice for subscription
- `_prepare_invoice()` - Prepare invoice values
- `action_generate_khqr()` - Generate KHQR QR code
- `action_mark_as_paid()` - Mark payment as paid and reconcile invoice

#### 2. khqr.payment.wizard (New)

**Purpose:** User-friendly wizard for KHQR payment setup

**Fields:**
- `subscription_id` - Link to subscription
- `partner_id` - Customer
- `company_id` - Company
- `amount` - Payment amount
- `currency_id` - Currency
- `partner_bank_id` - Bank account for payment
- `qr_code_data` - Generated QR code data
- `qr_code_image` - Generated QR code image
- `invoice_id` - Related invoice

**Methods:**
- `action_generate_qr_code()` - Generate KHQR QR code
- `action_confirm_payment()` - Confirm and close wizard
- `action_cancel()` - Cancel wizard

### Views

#### Subscription Form View (Enhanced)

**Header Buttons:**
- "Setup KHQR Payment" - Launch KHQR payment wizard
- "Quick Generate KHQR" - Quick generate without wizard (if bank account already selected)
- "Generate Invoice" - Generate invoice for subscription
- "Mark as Paid" - Mark payment as received

**New Sections:**
- "KHQR Payment" group - Shows QR code when generated
- Bank account field in Payment Information section
- Invoice button in button box

#### KHQR Payment Wizard View

**Features:**
- Clean, step-by-step interface
- Subscription and payment details display
- Bank account selection
- QR code generation and display
- Instructions for payment

### Security

**Access Rights:**
- All user groups can access KHQR wizard
- Public users can view but not modify subscriptions
- Standard users can create and modify their subscriptions
- Managers have full access

### Workflow

#### Creating KHQR Payment

1. **Select Payment Method**
   - Set subscription payment method to "KHQR (Bakong)"

2. **Generate Invoice** (Optional)
   - Click "Generate Invoice" button
   - Invoice is automatically created with subscription details

3. **Setup KHQR Payment**
   - Click "Setup KHQR Payment" button
   - Wizard opens with subscription details pre-filled

4. **Select Bank Account**
   - Choose a bank account configured with Bakong ID
   - Must be a Cambodian (KH) bank account
   - Proxy type must be either:
     - Bakong Account ID (Solo Merchant)
     - Bakong Account ID (Corporate Merchant)

5. **Generate QR Code**
   - Click "Generate QR Code" button
   - QR code is generated with EMV standard format
   - QR code includes:
     - Merchant information
     - Payment amount
     - Currency
     - Subscription reference
     - Timestamp and expiry

6. **Display QR Code**
   - QR code image displayed in wizard
   - QR code also saved to subscription record
   - Can be scanned by any KHQR-compatible banking app

7. **Customer Payment**
   - Customer scans QR code with banking app
   - Completes payment in their app
   - Supported apps: ABA Mobile, ACLEDA Mobile, Wing, etc.

8. **Mark as Paid**
   - Once payment confirmed, click "Mark as Paid"
   - Subscription status updated to "Active"
   - Invoice marked as paid
   - Payment registered and reconciled

#### Quick Generate (Alternative)

If bank account already configured:
1. Select bank account in subscription form
2. Click "Quick Generate KHQR" button
3. QR code generated and displayed immediately

## Bank Account Configuration

### Requirements

For KHQR to work, you need a bank account configured with:

1. **Country Code:** KH (Cambodia)
2. **Proxy Type:** Either:
   - Bakong Account ID (Solo Merchant)
   - Bakong Account ID (Corporate Merchant)
3. **Proxy Value:** Valid Bakong Account ID (format: username@bank)
4. **Merchant ID:** Required for Corporate Merchant accounts
5. **Bank:** Cambodian bank

### Setup Steps

1. Go to Accounting → Configuration → Bank Accounts
2. Create new bank account or edit existing
3. Set country to "Cambodia (KH)"
4. Select proxy type (Solo or Corporate Merchant)
5. Enter Bakong Account ID
6. For Corporate Merchant, also enter Merchant ID
7. Enter merchant name and city (required for QR code)
8. Save

## Supported Banks

KHQR is supported by all major Cambodian banks:
- ABA Bank
- ACLEDA Bank
- Wing Bank
- Prince Bank
- Canadia Bank
- Phillip Bank
- And many more...

## Currency Support

KHQR supports two currencies:
- **KHR** - Cambodian Riel
- **USD** - US Dollar

## API Integration

### Get QR Code via API

The QR code image can be accessed via URL:
```
{base_url}/web/image/hr.subscription/{subscription_id}/qr_code_image
```

### Fields for API

When working with subscriptions via API, the following fields are available:

**Input:**
- `payment_method` - Set to 'khqr'
- `partner_bank_id` - ID of bank account
- `amount` / `discounted_price` - Payment amount

**Output:**
- `qr_code_data` - EMV QR code string
- `qr_code_image` - Base64 encoded QR code image
- `qr_code_url` - Direct URL to QR code image
- `show_qr_code` - Boolean indicating if QR code should be displayed
- `invoice_id` - Related invoice
- `invoice_count` - Number of invoices

## QR Code Format

The KHQR code follows the EMV Merchant-Presented QR Code standard:

**Structure:**
- Payload Format Indicator (tag 00)
- Point of Initiation Method (tag 01) - Dynamic QR
- Merchant Account Information (tag 29 or 30)
  - For Solo: Bakong ID only
  - For Corporate: Bakong ID + Merchant ID + Bank Name
- Merchant Category Code (tag 52) - '0001'
- Transaction Currency (tag 53) - '116' (KHR) or '840' (USD)
- Transaction Amount (tag 54)
- Country Code (tag 58) - 'KH'
- Merchant Name (tag 59)
- Merchant City (tag 60)
- Additional Data Field (tag 62) - Subscription reference
- Timestamp (tag 99) - Current timestamp + expiry (30 days)
- CRC16 Checksum (tag 63)

## Error Handling

The implementation includes comprehensive error handling:

### Validation Errors
- Missing bank account
- Invalid proxy type
- Missing merchant ID (for corporate accounts)
- Invalid Bakong ID format
- Unsupported currency
- Invalid amount

### User Messages
All errors show user-friendly messages explaining:
- What went wrong
- What needs to be fixed
- How to fix it

## Testing

### Test Scenarios

1. **Generate KHQR for new subscription**
   - Create subscription with KHQR payment
   - Generate QR code
   - Verify QR code data and image

2. **Generate invoice first**
   - Create subscription
   - Generate invoice
   - Then generate QR code
   - Verify invoice linked correctly

3. **Mark as paid**
   - Generate KHQR
   - Mark as paid
   - Verify payment registered
   - Verify invoice reconciled

4. **Different currencies**
   - Test with KHR
   - Test with USD
   - Verify correct currency code in QR

5. **Solo vs Corporate Merchant**
   - Test with solo merchant account
   - Test with corporate merchant account
   - Verify correct merchant info in QR

### Demo Data

Demo subscriptions with KHQR payment are available in:
- `demo/hr_subscription_demo.xml`

## Troubleshooting

### QR Code Not Generating

**Possible Causes:**
1. Bank account not configured
2. Invalid Bakong ID
3. Missing merchant information
4. Unsupported currency

**Solution:**
- Check bank account configuration
- Verify Bakong ID format: username@bank
- Ensure merchant name and city are set
- Use only KHR or USD currency

### QR Code Not Displaying

**Possible Causes:**
1. Payment method not set to KHQR
2. Payment already marked as paid
3. QR code not generated yet

**Solution:**
- Set payment method to 'khqr'
- Ensure payment_status is 'pending'
- Click "Generate KHQR" button

### Payment Not Reconciling

**Possible Causes:**
1. Invoice not posted
2. Journal not configured
3. Payment method not configured

**Solution:**
- Ensure invoice is in 'Posted' state
- Configure sales journal for company
- Configure payment method for journal

## Future Enhancements

Potential improvements for future versions:

1. **Automatic Payment Verification**
   - Integration with bank APIs
   - Automatic payment status updates
   - Real-time payment notifications

2. **Payment History**
   - Track all payment attempts
   - Store QR code history
   - Payment timeline view

3. **Multi-Currency Exchange**
   - Automatic currency conversion
   - Display amount in both KHR and USD
   - Real-time exchange rates

4. **Batch Payments**
   - Generate QR codes for multiple subscriptions
   - Bulk payment processing
   - Payment batch reports

5. **Mobile App Integration**
   - Direct QR code scanning in mobile app
   - Push notifications for payment
   - Mobile payment confirmation

## Support

For issues or questions about KHQR implementation:
1. Check this documentation
2. Review error messages
3. Verify bank account configuration
4. Contact your Odoo administrator

## References

- [KHQR Standard Documentation](https://bakong.nbc.gov.kh)
- [EMV QR Code Specification](https://www.emvco.com)
- [Odoo Account Module](https://www.odoo.com/documentation/18.0/applications/finance/accounting.html)
- [Cambodia Payment Systems](https://www.nbc.gov.kh)

