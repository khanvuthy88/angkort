# Quick Start Guide: Default User Templates

## Overview

This feature creates default inactive user templates for candidates and employers. When new users sign up, they are created by copying these templates, ensuring consistency in permissions and settings.

## Quick Installation

### 1. Upgrade the Module

**Option A: Command Line**
```bash
cd /path/to/odoo
./odoo-bin -u angkot_recruitement -d your_database
```

**Option B: Web Interface**
1. Go to Apps (enable Developer Mode if needed)
2. Remove "Apps" filter to see all modules
3. Search for "Angkot Recruitment Enhancement"
4. Click "Upgrade"

### 2. Verify Installation

After upgrade, check that default users were created:

**In Odoo Shell:**
```python
# Start Odoo shell
./odoo-bin shell -d your_database

# Check default users exist
candidate = env.ref('angkot_recruitement.default_candidate_user')
employer = env.ref('angkot_recruitement.default_employer_user')

print(f"✓ Candidate Template: {candidate.name} (Active: {candidate.active})")
print(f"✓ Employer Template: {employer.name} (Active: {employer.active})")
print(f"\nCandidate Groups: {candidate.groups_id.mapped('name')}")
print(f"Employer Groups: {employer.groups_id.mapped('name')}")
```

**Expected Output:**
```
✓ Candidate Template: Default Candidate Template (Active: False)
✓ Employer Template: Default Employer Template (Active: False)

Candidate Groups: ['User types / Internal User', 'Job Applicant']
Employer Groups: ['User types / Internal User', 'Recruitment Officer']
```

**In Web UI:**
1. Enable Developer Mode: Settings → Activate Developer Mode
2. Go to Settings → Users & Companies → Users
3. Remove "Active" filter (click "Active" chip to remove it)
4. You should see two inactive users:
   - Default Candidate Template (default_candidate@template.local)
   - Default Employer Template (default_employer@template.local)

## Testing

### Automated Testing

Run the provided test script:

```bash
cd /path/to/angkot_recruitement
python3 test_default_users.py
```

This will:
- Test candidate signup using the template
- Test employer signup using the template
- Show detailed results and verification steps

### Manual Testing

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

### Check Odoo Logs

After signup, check Odoo logs for confirmation:

```bash
tail -f /path/to/odoo/odoo.log | grep "default user template"
```

**Expected log entries:**
```
INFO ... Using default user template: angkot_recruitement.default_candidate_user (ID: 123)
INFO ... User created from template: ID=456, login=test.candidate@example.com, groups=['Internal User', 'Job Applicant']
```

## How It Works

### Before (Old Method)
```
Signup Request
    ↓
Create new user from scratch
    ↓
Manually assign groups
    ↓
Set all fields individually
```

### After (New Method)
```
Signup Request
    ↓
Find appropriate template user
    ↓
Copy template (inherits all settings)
    ↓
Update with user's details
    ↓
Activate and set password
```

## Customization

### Add Default Values to Templates

**Example: Set default timezone and language**

1. Go to Settings → Users & Companies → Users
2. Remove "Active" filter
3. Open "Default Candidate Template"
4. Edit fields:
   - Timezone: Asia/Phnom_Penh
   - Language: Khmer / ភាសាខ្មែរ (km_KH)
5. Save

Now all new candidates will have these defaults!

### Add Additional Groups

**Via XML (requires module upgrade):**

Edit `data/default_users_data.xml`:
```xml
<record id="default_candidate_user" model="res.users">
    <!-- ... existing fields ... -->
    <field name="groups_id" eval="[
        (4, ref('base.group_user')),
        (4, ref('angkot_recruitement.group_hr_recruitment_applicant')),
        (4, ref('your_module.your_custom_group'))
    ]"/>
</record>
```

**Via Web UI (no upgrade needed):**
1. Open default user template
2. Go to "Access Rights" tab
3. Add groups as needed
4. All future signups inherit these groups

## Troubleshooting

### Issue: "Default user template not found"

**Check 1: Module upgraded?**
```bash
./odoo-bin -u angkot_recruitement -d your_database
```

**Check 2: Data file loaded?**
```python
# In Odoo shell
print('default_users_data.xml' in env['ir.model.data'].search([
    ('module', '=', 'angkot_recruitement')
]).mapped('model'))
```

**Check 3: XML IDs exist?**
```python
# In Odoo shell
try:
    candidate = env.ref('angkot_recruitement.default_candidate_user')
    print(f"✓ Candidate template found: {candidate.id}")
except ValueError as e:
    print(f"✗ Candidate template not found: {e}")

try:
    employer = env.ref('angkot_recruitement.default_employer_user')
    print(f"✓ Employer template found: {employer.id}")
except ValueError as e:
    print(f"✗ Employer template not found: {e}")
```

**Fix: Force reinstall data**
```bash
# WARNING: This will reset all noupdate=1 data
./odoo-bin -u angkot_recruitement -d your_database --init angkot_recruitement
```

### Issue: Users created but wrong groups

**Check template groups:**
```python
# In Odoo shell
candidate = env.ref('angkot_recruitement.default_candidate_user')
print("Template groups:", candidate.groups_id.mapped('name'))

# Check a newly created user
user = env['res.users'].search([('login', '=', 'test.candidate@example.com')])
print("User groups:", user.groups_id.mapped('name'))
```

**Fix: Update template groups**
```python
# In Odoo shell (as admin)
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

### Issue: Template users show in user list

**This is normal!** Template users are inactive by default.

**To hide them from regular views:**
- User lists usually have an "Active" filter enabled by default
- Templates only show when you remove the "Active" filter
- They have distinctive names: "Default Candidate Template", etc.

## Files Changed

1. **New File:** `data/default_users_data.xml`
   - Contains default user template definitions

2. **Modified:** `__manifest__.py`
   - Added `data/default_users_data.xml` to data list

3. **Modified:** `controllers/controllers.py`
   - Added `_copy_default_user()` method
   - Updated `signup()` to use templates

4. **New File:** `DEFAULT_USER_TEMPLATES.md`
   - Comprehensive documentation

5. **New File:** `test_default_users.py`
   - Automated test script

6. **New File:** `QUICKSTART_DEFAULT_USERS.md` (this file)
   - Quick reference guide

## Benefits

✓ **Consistency**: All users of same type have identical permissions
✓ **Maintainability**: Change template, affect all future users
✓ **Performance**: Copying is faster than creating from scratch
✓ **Flexibility**: Customize templates without code changes
✓ **Error Prevention**: No manual group assignment errors

## Next Steps

After installation and testing:

1. **Customize templates** for your specific needs
2. **Add company branding** (logo, signature, etc.) to templates
3. **Set default preferences** (language, timezone, notifications)
4. **Document customizations** for your team
5. **Test in production** with real signups

## Support

For issues or questions:
1. Check Odoo server logs
2. Review `DEFAULT_USER_TEMPLATES.md` for detailed documentation
3. Run `test_default_users.py` to diagnose issues
4. Verify templates exist and are properly configured

## Rollback (if needed)

To revert to old method:

1. **Backup your database first!**

2. **Restore old signup code:**
   ```bash
   git checkout HEAD~1 -- controllers/controllers.py
   ```

3. **Remove data file:**
   - Remove `data/default_users_data.xml` from `__manifest__.py`

4. **Upgrade module:**
   ```bash
   ./odoo-bin -u angkot_recruitement -d your_database
   ```

Note: Existing users created with templates will continue to work normally.

