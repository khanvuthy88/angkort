# Default User Templates - Complete Guide

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [What This Feature Does](#what-this-feature-does)
3. [Files Overview](#files-overview)
4. [Installation](#installation)
5. [Testing](#testing)
6. [Customization](#customization)
7. [Troubleshooting](#troubleshooting)
8. [Documentation](#documentation)

## 🚀 Quick Start

### Installation (3 steps)

```bash
# 1. Upgrade the module
./odoo-bin -u angkot_recruitement -d your_database

# 2. Verify templates were created (in Odoo shell)
./odoo-bin shell -d your_database
>>> candidate = env.ref('angkot_recruitement.default_candidate_user')
>>> employer = env.ref('angkot_recruitement.default_employer_user')
>>> print(f"✓ Candidate: {candidate.name}")
>>> print(f"✓ Employer: {employer.name}")

# 3. Test signup
python3 test_default_users.py
```

## 💡 What This Feature Does

Creates **inactive template users** that serve as blueprints for new user accounts. When someone signs up as a candidate or employer, their account is created by **copying the appropriate template**, ensuring:

- ✅ Consistent permissions across all users of the same type
- ✅ Easier maintenance (update template → affects all future users)
- ✅ Faster user creation (copy vs create from scratch)
- ✅ No code changes needed to modify default settings

### Before & After

**Before (Old Method):**
```python
# ~70 lines of code
# Manual group assignment
# Hard-coded company IDs
# Changes require code updates
```

**After (New Method):**
```python
# ~20 lines of code
# Automatic group inheritance
# Template-based configuration
# Changes via Odoo UI
```

## 📁 Files Overview

### Core Implementation Files

| File | Purpose | Lines |
|------|---------|-------|
| `data/default_users_data.xml` | Template user definitions | 40 |
| `controllers/controllers.py` | Copy logic + signup method | Modified |
| `__manifest__.py` | Module configuration | Updated |

### Documentation Files

| File | Purpose | Best For |
|------|---------|----------|
| `README_DEFAULT_USERS.md` | This file - overview and quick reference | Getting started |
| `QUICKSTART_DEFAULT_USERS.md` | Installation and basic usage | First-time setup |
| `DEFAULT_USER_TEMPLATES.md` | Comprehensive technical documentation | Deep dive |
| `DEFAULT_USER_IMPLEMENTATION_SUMMARY.md` | High-level summary | Management/overview |
| `DEFAULT_USER_FLOW_DIAGRAM.md` | Visual flow diagrams | Understanding the system |

### Testing Files

| File | Purpose |
|------|---------|
| `test_default_users.py` | Automated test script |

## 🔧 Installation

### Method 1: Web Interface (Recommended)

1. **Enable Developer Mode**
   - Settings → Activate Developer Mode

2. **Upgrade Module**
   - Apps → Remove "Apps" filter
   - Search: "Angkot Recruitment Enhancement"
   - Click: "Upgrade"

3. **Verify Templates**
   - Settings → Users & Companies → Users
   - Remove "Active" filter
   - Look for:
     - Default Candidate Template
     - Default Employer Template

### Method 2: Command Line

```bash
# Navigate to Odoo directory
cd /path/to/odoo

# Upgrade module
./odoo-bin -u angkot_recruitement -d your_database

# Restart Odoo
sudo systemctl restart odoo
```

### Verification

**Check in Odoo Shell:**
```python
./odoo-bin shell -d your_database

# Verify templates exist
candidate = env.ref('angkot_recruitement.default_candidate_user')
employer = env.ref('angkot_recruitement.default_employer_user')

print(f"Candidate Template:")
print(f"  Name: {candidate.name}")
print(f"  Active: {candidate.active}")
print(f"  Groups: {candidate.groups_id.mapped('name')}")

print(f"\nEmployer Template:")
print(f"  Name: {employer.name}")
print(f"  Active: {employer.active}")
print(f"  Groups: {employer.groups_id.mapped('name')}")
```

**Expected Output:**
```
Candidate Template:
  Name: Default Candidate Template
  Active: False
  Groups: ['User types / Internal User', 'Job Applicant']

Employer Template:
  Name: Default Employer Template
  Active: False
  Groups: ['User types / Internal User', 'Recruitment Officer']
```

## 🧪 Testing

### Automated Test

```bash
cd /path/to/angkot_recruitement
python3 test_default_users.py
```

**What it tests:**
- ✓ Candidate signup using template
- ✓ Employer signup using template
- ✓ Correct group assignment
- ✓ Proper role assignment
- ✓ Permission validation

### Manual API Test

**Test Candidate Signup:**
```bash
curl -X POST http://localhost:8069/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Candidate",
    "email": "test.candidate@example.com",
    "password": "test123",
    "phone": "012345678",
    "user_type": "candidate"
  }'
```

**Test Employer Signup:**
```bash
curl -X POST http://localhost:8069/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Employer",
    "email": "test.employer@example.com",
    "password": "test123",
    "phone": "098765432",
    "user_type": "employer"
  }'
```

### Check Logs

```bash
# Monitor Odoo logs during signup
tail -f /var/log/odoo/odoo.log | grep "default user template"
```

**Expected log entries:**
```
INFO ... Using default user template: angkot_recruitement.default_candidate_user (ID: 10)
INFO ... User created from template: ID=123, login=test.candidate@example.com, groups=['Internal User', 'Job Applicant']
```

## 🎨 Customization

### Customize Templates via UI

**No code changes required!** Admins can modify templates directly in Odoo:

1. **Access Templates**
   - Settings → Users & Companies → Users
   - Remove "Active" filter
   - Find "Default Candidate Template" or "Default Employer Template"

2. **Edit Settings**
   - **General Tab:** Name, email, phone, company
   - **Access Rights Tab:** Groups and permissions
   - **Preferences Tab:** Language, timezone, signature
   - **Other Tab:** Custom fields

3. **Save Changes**
   - All future signups automatically inherit the new settings!

### Common Customizations

#### Set Default Timezone

```python
# In Odoo shell or via UI
candidate = env.ref('angkot_recruitement.default_candidate_user')
candidate.write({'tz': 'Asia/Phnom_Penh'})
```

#### Set Default Language

```python
candidate = env.ref('angkot_recruitement.default_candidate_user')
candidate.write({'lang': 'km_KH'})  # Khmer
```

#### Add Email Signature

```python
candidate = env.ref('angkot_recruitement.default_candidate_user')
candidate.write({
    'signature': '<p>Best regards,<br/>Your Name<br/>Company Name</p>'
})
```

#### Add Additional Groups

```python
# Add a custom group to all new candidates
candidate = env.ref('angkot_recruitement.default_candidate_user')
custom_group = env.ref('your_module.your_custom_group')
candidate.write({
    'groups_id': [(4, custom_group.id)]
})
```

### Advanced: Multiple Templates

You can create additional templates for specific scenarios:

```xml
<!-- In your custom data file -->
<record id="default_premium_candidate_user" model="res.users">
    <field name="name">Premium Candidate Template</field>
    <field name="login">default_premium@template.local</field>
    <field name="active" eval="False"/>
    <field name="groups_id" eval="[
        (4, ref('base.group_user')),
        (4, ref('angkot_recruitement.group_hr_recruitment_applicant')),
        (4, ref('your_module.group_premium_features'))
    ]"/>
</record>
```

## 🔍 Troubleshooting

### Issue: "Default user template not found"

**Symptoms:**
- Signup fails with error message
- Logs show: `Default user template not found`

**Solutions:**

1. **Verify module upgrade:**
   ```bash
   ./odoo-bin -u angkot_recruitement -d your_database
   ```

2. **Check if templates exist:**
   ```python
   # In Odoo shell
   try:
       candidate = env.ref('angkot_recruitement.default_candidate_user')
       print(f"✓ Found: {candidate.name}")
   except ValueError:
       print("✗ Candidate template not found")
   ```

3. **Force data reload (last resort):**
   ```bash
   # WARNING: Resets all noupdate=1 data
   ./odoo-bin -u angkot_recruitement -d your_database --init angkot_recruitement
   ```

### Issue: Users created but have wrong groups

**Symptoms:**
- Users can't access expected features
- Permission denied errors

**Solutions:**

1. **Check template groups:**
   ```python
   # In Odoo shell
   candidate = env.ref('angkot_recruitement.default_candidate_user')
   print("Template groups:", candidate.groups_id.mapped('name'))
   
   user = env['res.users'].search([('login', '=', 'user@example.com')])
   print("User groups:", user.groups_id.mapped('name'))
   ```

2. **Update template groups:**
   ```python
   candidate = env.ref('angkot_recruitement.default_candidate_user')
   candidate.write({
       'groups_id': [
           (6, 0, [
               env.ref('base.group_user').id,
               env.ref('angkot_recruitement.group_hr_recruitment_applicant').id
           ])
       ]
   })
   ```

3. **Test with new signup** to verify fix

### Issue: Template users visible in user list

**This is normal!** Templates are inactive users.

**To hide them:**
- Ensure "Active" filter is enabled in Users list
- Templates only show when "Active" filter is removed
- They're easily identifiable by name: "Default ... Template"

### Issue: Module upgrade fails

**Common causes:**
1. XML syntax error in `default_users_data.xml`
2. Security groups don't exist yet
3. Data file loaded before security files

**Solutions:**

1. **Check XML syntax:**
   ```bash
   xmllint --noout data/default_users_data.xml
   ```

2. **Verify load order in `__manifest__.py`:**
   ```python
   'data': [
       'security/hr_recruitment_security.xml',  # MUST be first
       'security/ir.model.access.xml',
       'security/ir.model.access.csv',
       'data/default_users_data.xml',  # After security
       # ... other files
   ]
   ```

3. **Check Odoo logs:**
   ```bash
   tail -100 /var/log/odoo/odoo.log | grep -i error
   ```

## 📚 Documentation

### Quick Reference

- **Installation:** `QUICKSTART_DEFAULT_USERS.md`
- **Technical Details:** `DEFAULT_USER_TEMPLATES.md`
- **System Overview:** `DEFAULT_USER_IMPLEMENTATION_SUMMARY.md`
- **Flow Diagrams:** `DEFAULT_USER_FLOW_DIAGRAM.md`

### Code Reference

**Template Definition:** `data/default_users_data.xml`
```xml
<record id="default_candidate_user" model="res.users">
    <field name="name">Default Candidate Template</field>
    <field name="active" eval="False"/>
    <!-- ... -->
</record>
```

**Copy Method:** `controllers/controllers.py`
```python
def _copy_default_user(self, user_type, name, email, password, phone=''):
    # Find template
    # Copy with new values
    # Set password
    # Return new user
```

**Signup Usage:** `controllers/controllers.py`
```python
def signup(self, **kwargs):
    # ... validation ...
    new_user = self._copy_default_user(user_type, name, email, password, phone)
    # ... rest of signup ...
```

## 🎯 Best Practices

1. **Test in Staging First**
   - Always test template changes in a staging environment
   - Verify signups work correctly before deploying to production

2. **Document Customizations**
   - Keep track of any custom fields or groups added to templates
   - Document why specific settings were chosen

3. **Regular Audits**
   - Periodically review template configurations
   - Ensure groups and permissions are still appropriate
   - Remove deprecated settings

4. **Backup Before Changes**
   - Always backup database before modifying templates
   - Test new signups after template modifications

5. **Don't Delete Templates**
   - Keep templates inactive but don't delete them
   - System requires them for signup to work
   - If deleted, recreate via module upgrade

## 🔐 Security Notes

- ✅ Template users are **inactive** - cannot log in
- ✅ Template emails use `.local` domain - no conflicts
- ✅ Templates have **no passwords** - cannot authenticate
- ✅ `copy()` creates **independent records** - no shared state
- ✅ All operations are **logged** for security auditing

## 🚦 Status Indicators

After implementation, check these:

| Indicator | Status | How to Check |
|-----------|--------|--------------|
| Templates Exist | ✅ | Odoo shell: `env.ref('angkot_recruitement.default_candidate_user')` |
| Templates Inactive | ✅ | UI: Users list (remove Active filter) |
| Correct Groups | ✅ | Shell: `template.groups_id.mapped('name')` |
| Signups Working | ✅ | Test script: `python3 test_default_users.py` |
| Logs Clean | ✅ | No errors in Odoo logs during signup |

## 📞 Support

### Self-Service
1. Check this README
2. Review `QUICKSTART_DEFAULT_USERS.md`
3. Run `test_default_users.py`
4. Check Odoo server logs

### Debug Checklist
- [ ] Module upgraded successfully
- [ ] Templates exist (check in Odoo shell)
- [ ] Templates have correct groups
- [ ] Security groups loaded before templates
- [ ] No errors in Odoo logs
- [ ] Test signup completes successfully

## 📝 Summary

This feature provides a robust, maintainable template-based user creation system that:

- **Reduces code complexity** by 70%
- **Improves consistency** across all user signups
- **Enables UI-based configuration** without code changes
- **Maintains backward compatibility** with existing code
- **Includes comprehensive testing** and documentation

The system is production-ready and has been thoroughly tested.

---

**Version:** 1.0  
**Last Updated:** October 12, 2025  
**Module:** Angkot Recruitment Enhancement  
**Status:** ✅ Production Ready

