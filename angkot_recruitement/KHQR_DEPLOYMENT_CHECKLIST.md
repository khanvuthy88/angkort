# KHQR Payment - Deployment Checklist

## Pre-Deployment Checklist

### 1. Module Installation ✓

- [x] Module dependencies added to `__manifest__.py`
  - `account`
  - `l10n_kh`
  - `account_qr_code_emv`

- [x] Wizard module imported in `__init__.py`

- [x] Views added to manifest data files
  - `wizard/khqr_payment_wizard_views.xml`

- [x] Security access rights configured
  - `ir.model.access.csv` updated with wizard permissions

### 2. Code Implementation ✓

**Models:**
- [x] `hr.subscription` enhanced with KHQR fields
- [x] `khqr.payment.wizard` created
- [x] Invoice generation methods added
- [x] QR code generation methods added
- [x] Payment reconciliation methods added

**Views:**
- [x] Subscription form view updated
- [x] KHQR payment section added
- [x] Wizard form view created
- [x] List view updated with payment method
- [x] Search filters added for KHQR

**Wizard:**
- [x] Wizard model created
- [x] Wizard view created
- [x] Wizard actions configured
- [x] Wizard security configured

### 3. Documentation ✓

- [x] Technical documentation (KHQR_PAYMENT_IMPLEMENTATION.md)
- [x] Quick start guide (KHQR_QUICKSTART.md)
- [x] Implementation summary (KHQR_IMPLEMENTATION_SUMMARY.md)
- [x] Deployment checklist (this file)

## Deployment Steps

### Step 1: Database Backup ⚠️

**CRITICAL:** Always backup before deployment!

```bash
# Backup database
pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup filestore
tar -czf filestore_backup_$(date +%Y%m%d_%H%M%S).tar.gz ~/.local/share/Odoo/filestore/your_database/
```

- [ ] Database backup completed
- [ ] Filestore backup completed
- [ ] Backup verified and accessible

### Step 2: Update Module

```bash
# Navigate to Odoo directory
cd /path/to/odoo

# Update module
./odoo-bin -d your_database -u angkot_recruitement

# Or with specific config
./odoo-bin -c /path/to/odoo.conf -d your_database -u angkot_recruitement
```

- [ ] Module update command executed
- [ ] No errors during update
- [ ] Server restarted successfully

### Step 3: Verify Installation

**Check Module:**
- [ ] Navigate to Apps menu
- [ ] Search for "Angkot Recruitment"
- [ ] Verify version updated
- [ ] Check dependencies installed
  - [ ] `account` installed
  - [ ] `l10n_kh` installed
  - [ ] `account_qr_code_emv` installed

**Check Models:**
- [ ] Access HR → Subscriptions
- [ ] Open any subscription
- [ ] Verify new fields visible:
  - [ ] Payment method has "KHQR (Bakong)" option
  - [ ] Bank Account field visible
  - [ ] KHQR Payment section exists

**Check Wizard:**
- [ ] Create test subscription with KHQR payment
- [ ] Click "Setup KHQR Payment" button
- [ ] Wizard opens successfully
- [ ] All fields visible and functional

### Step 4: Configure Bank Accounts

**Create Test Bank Account:**

1. Navigate to: **Accounting → Configuration → Bank Accounts**

2. Create new bank account:
   ```
   Account Holder: Your Company Name
   Bank: [Select Cambodian bank]
   Account Number: [Real or test account]
   Country: Cambodia (KH)
   
   KHQR Configuration:
   ├─ Proxy Type: Bakong Account ID (Solo Merchant)
   ├─ Proxy Value: testcompany@aba
   └─ Partner: Your Company
   ```

3. Save and verify:
   - [ ] Bank account created
   - [ ] Country is KH
   - [ ] Proxy type is Bakong ID
   - [ ] Proxy value is valid format (xxx@bank)

**Create Production Bank Accounts:**
- [ ] Solo merchant account configured
- [ ] Corporate merchant account configured (if applicable)
- [ ] Merchant name and city set
- [ ] All required fields filled

### Step 5: Test Payment Flow

**Test 1: Wizard Flow**
1. Create test subscription:
   ```
   User: Test User
   Plan: Basic Plan
   Payment Method: KHQR (Bakong)
   ```
   - [ ] Subscription created successfully

2. Setup KHQR payment:
   - [ ] Click "Setup KHQR Payment" button
   - [ ] Wizard opens
   - [ ] Subscription details displayed correctly
   - [ ] Bank account dropdown shows configured accounts

3. Generate QR code:
   - [ ] Select bank account
   - [ ] Click "Generate QR Code"
   - [ ] QR code data generated
   - [ ] QR code image displayed
   - [ ] No errors

4. Verify QR code:
   - [ ] QR code visible in wizard
   - [ ] QR code saved to subscription
   - [ ] QR code visible in subscription form

**Test 2: Quick Generate**
1. Create another subscription with KHQR
   - [ ] Subscription created

2. Quick generate:
   - [ ] Select bank account directly
   - [ ] Click "Quick Generate KHQR"
   - [ ] QR code generated immediately
   - [ ] QR code displayed

**Test 3: Invoice Generation**
1. On test subscription:
   - [ ] Click "Generate Invoice"
   - [ ] Invoice created successfully
   - [ ] Invoice linked to subscription
   - [ ] Invoice amount correct

**Test 4: Payment Confirmation**
1. Mark as paid:
   - [ ] Click "Mark as Paid"
   - [ ] Payment status updated to "Paid"
   - [ ] Payment date recorded
   - [ ] Subscription activated (if was pending)
   - [ ] Invoice reconciled (if posted)

**Test 5: QR Code Scanning** (Optional but Recommended)
1. Generate real QR code with test amount
2. Scan with banking app:
   - [ ] ABA Mobile can read QR
   - [ ] ACLEDA Mobile can read QR
   - [ ] Wing app can read QR
   - [ ] Merchant info displayed correctly
   - [ ] Amount displayed correctly
   - [ ] Currency correct (KHR or USD)

### Step 6: Security Verification

**Access Rights:**
- [ ] Public users: Can view subscriptions, cannot modify
- [ ] Standard users: Can create/modify their subscriptions
- [ ] Officers: Can manage subscriptions, cannot delete
- [ ] Managers: Full access to all subscriptions
- [ ] All groups can access wizard

**Data Security:**
- [ ] Bank accounts filtered by company
- [ ] Only KH bank accounts selectable for KHQR
- [ ] Users cannot modify paid subscriptions
- [ ] Invoice security maintained

### Step 7: User Training

**Train Staff:**
- [ ] Show how to configure bank accounts
- [ ] Demonstrate wizard workflow
- [ ] Explain quick generate
- [ ] Show payment confirmation process
- [ ] Cover error handling

**Create User Documentation:**
- [ ] Share KHQR_QUICKSTART.md with users
- [ ] Create video tutorial (optional)
- [ ] Prepare FAQ document
- [ ] Set up support channel

### Step 8: Monitoring Setup

**Logging:**
- [ ] Enable INFO level logging for hr_subscription
- [ ] Monitor QR code generation logs
- [ ] Track payment confirmations
- [ ] Watch for errors

**Alerts:**
- [ ] Set up alert for failed QR generations
- [ ] Monitor unpaid subscriptions
- [ ] Track payment delays
- [ ] Review error rates

**Reports:**
- [ ] KHQR payments report
- [ ] Payment success rate
- [ ] Average payment time
- [ ] Popular payment methods

## Post-Deployment Checklist

### Day 1: Launch Day

**Morning:**
- [ ] Verify system is running
- [ ] Check no errors in logs
- [ ] Test QR generation
- [ ] Monitor user activity

**Afternoon:**
- [ ] Review first payments
- [ ] Check QR code scans
- [ ] Verify invoice reconciliation
- [ ] Support first users

**Evening:**
- [ ] Review day's statistics
- [ ] Check for any issues
- [ ] Document lessons learned
- [ ] Plan improvements

### Week 1: First Week

- [ ] Monitor daily usage
- [ ] Collect user feedback
- [ ] Fix any minor issues
- [ ] Optimize workflows
- [ ] Update documentation

### Month 1: First Month

- [ ] Review payment success rate
- [ ] Analyze QR code usage
- [ ] Evaluate user satisfaction
- [ ] Plan enhancements
- [ ] Update training materials

## Rollback Plan

**If Issues Occur:**

1. **Identify Issue:**
   - Check error logs
   - Review recent changes
   - Document the problem

2. **Quick Fix Attempt:**
   - Try configuration changes
   - Check bank account setup
   - Verify permissions

3. **Rollback if Needed:**
   ```bash
   # Stop Odoo
   sudo systemctl stop odoo
   
   # Restore database
   psql -d your_database < backup_YYYYMMDD_HHMMSS.sql
   
   # Restore filestore
   tar -xzf filestore_backup_YYYYMMDD_HHMMSS.tar.gz -C ~/.local/share/Odoo/filestore/
   
   # Start Odoo
   sudo systemctl start odoo
   ```

4. **Verify Rollback:**
   - [ ] System running
   - [ ] Data intact
   - [ ] Users can access
   - [ ] Document issue for future fix

## Success Criteria

**Technical Success:**
- ✅ Module installs without errors
- ✅ All features working as designed
- ✅ QR codes generate correctly
- ✅ Payments reconcile properly
- ✅ No security issues

**User Success:**
- ✅ Users can generate QR codes
- ✅ Customers can scan and pay
- ✅ Staff can confirm payments
- ✅ Process is faster than before
- ✅ Fewer payment errors

**Business Success:**
- ✅ Payments processed faster
- ✅ Reduced manual work
- ✅ Better customer experience
- ✅ Accurate financial records
- ✅ Ready for scaling

## Support Contacts

**Technical Issues:**
- Module Developer: [Your Contact]
- System Administrator: [Admin Contact]
- Odoo Support: support@odoo.com

**Business Issues:**
- Finance Team: [Finance Contact]
- Customer Service: [CS Contact]
- Management: [Manager Contact]

**Banking Issues:**
- Bank Support: [Your Bank Contact]
- Bakong Support: support@bakong.nbc.gov.kh
- NBC Hotline: 023 969 369

## Additional Resources

**Documentation:**
- Technical Docs: `KHQR_PAYMENT_IMPLEMENTATION.md`
- Quick Start: `KHQR_QUICKSTART.md`
- Summary: `KHQR_IMPLEMENTATION_SUMMARY.md`

**External Resources:**
- [Bakong Website](https://bakong.nbc.gov.kh)
- [NBC Cambodia](https://www.nbc.gov.kh)
- [Odoo Documentation](https://www.odoo.com/documentation/18.0/)

## Sign-Off

**Deployment Completed:**

Date: _______________

**Verified By:**

- [ ] Developer: _________________ Date: _______
- [ ] System Admin: _________________ Date: _______
- [ ] Finance Manager: _________________ Date: _______
- [ ] Business Owner: _________________ Date: _______

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

**Status:** Ready for Deployment ✅

**Last Updated:** October 9, 2025

