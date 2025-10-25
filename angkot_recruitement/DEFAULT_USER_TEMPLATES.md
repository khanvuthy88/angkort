# Default User Templates Implementation

## Overview

This implementation provides a template-based user creation system for the recruitment module. Instead of creating users from scratch, the system now copies predefined inactive "default users" when new candidates or employers register. This approach ensures consistency in user permissions, settings, and configuration.

## Benefits

1. **Consistency**: All new users of the same type inherit identical permissions and settings
2. **Maintainability**: Changes to default users automatically affect all new registrations
3. **Performance**: Copying is faster than creating users from scratch
4. **Flexibility**: Administrators can customize default user settings in Odoo's UI
5. **Reduced Errors**: Eliminates manual group assignment errors during signup

## Architecture

### Default User Templates

Two inactive user templates are created during module installation:

1. **Default Candidate User** (`default_candidate_user`)
   - Login: `default_candidate@template.local`
   - Groups: `base.group_user` + `group_hr_recruitment_applicant`
   - Active: `False` (template only)
   
2. **Default Employer User** (`default_employer_user`)
   - Login: `default_employer@template.local`
   - Groups: `base.group_user` + `group_hr_recruitment_officer`
   - Active: `False` (template only)

### User Creation Flow

```
User Signup Request
        ↓
Check if user exists
        ↓
Select appropriate template (candidate/employer)
        ↓
Copy template user with new details
        ↓
Activate copied user
        ↓
Set password
        ↓
Create candidate profile (if applicable)
        ↓
Send verification email
```

## Implementation Details

### 1. Data File: `data/default_users_data.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        
        <!-- Default Candidate User Template (Inactive) -->
        <record id="default_candidate_user" model="res.users">
            <field name="name">Default Candidate Template</field>
            <field name="login">default_candidate@template.local</field>
            <field name="email">default_candidate@template.local</field>
            <field name="active" eval="False"/>
            <field name="company_id" ref="base.main_company"/>
            <field name="company_ids" eval="[(4, ref('base.main_company'))]"/>
            <field name="groups_id" eval="[
                (4, ref('base.group_user')),
                (4, ref('angkot_recruitement.group_hr_recruitment_applicant'))
            ]"/>
            <field name="email_verified" eval="False"/>
            <field name="notification_type">email</field>
        </record>

        <!-- Default Employer/Officer User Template (Inactive) -->
        <record id="default_employer_user" model="res.users">
            <field name="name">Default Employer Template</field>
            <field name="login">default_employer@template.local</field>
            <field name="email">default_employer@template.local</field>
            <field name="active" eval="False"/>
            <field name="company_id" ref="base.main_company"/>
            <field name="company_ids" eval="[(4, ref('base.main_company'))]"/>
            <field name="groups_id" eval="[
                (4, ref('base.group_user')),
                (4, ref('angkot_recruitement.group_hr_recruitment_officer'))
            ]"/>
            <field name="email_verified" eval="False"/>
            <field name="notification_type">email</field>
        </record>

    </data>
</odoo>
```

**Key Features:**
- `noupdate="1"`: Prevents data updates on module upgrades
- `active="False"`: Templates are inactive by default
- All necessary groups pre-assigned
- Email notification preference set

### 2. Controller Method: `_copy_default_user()`

```python
def _copy_default_user(self, user_type, name, email, password, phone=''):
    """
    Copy default user template based on user type
    
    Args:
        user_type: 'candidate' or 'employer'
        name: User's full name
        email: User's email
        password: User's password
        phone: User's phone number (optional)
    
    Returns:
        New user record or None if failed
    """
    try:
        # Get the default user template based on user type
        if user_type == 'candidate':
            default_user_xmlid = 'angkot_recruitement.default_candidate_user'
        else:
            default_user_xmlid = 'angkot_recruitement.default_employer_user'
        
        # Find the default user template (must search inactive users)
        default_user = request.env.ref(default_user_xmlid, raise_if_not_found=False)
        
        if not default_user:
            _logger.error(f"Default user template not found: {default_user_xmlid}")
            return None
        
        _logger.info(f"Using default user template: {default_user_xmlid} (ID: {default_user.id})")
        
        # Copy the default user with new values
        # We use copy() which duplicates the user with all groups and settings
        new_user = default_user.sudo().with_context(
            no_reset_password=True,
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True
        ).copy({
            'name': name,
            'login': email,
            'email': email,
            'phone': phone,
            'active': True,  # Activate the user (email verification will control access)
            'email_verified': False,  # Email not verified yet
        })
        
        # Set password after user is created
        if new_user:
            new_user.sudo().with_context(no_reset_password=True).write({'password': password})
            _logger.info(f"User created from template: ID={new_user.id}, login={new_user.login}, groups={new_user.groups_id.mapped('name')}")
        
        return new_user
        
    except Exception as e:
        _logger.error(f"Error copying default user for {user_type}: {str(e)}", exc_info=True)
        return None
```

**Key Features:**
- Uses Odoo's `copy()` method to duplicate user records
- Automatically inherits all groups and permissions from template
- Activates the new user (original template remains inactive)
- Sets password securely after creation
- Comprehensive logging for debugging

### 3. Updated Signup Method

The signup method now uses the template-based approach:

```python
# Determine role based on user type
role = 'job_applicant' if user_type == 'candidate' else 'recruitment_officer'

# Create user from default template
_logger.info(f"Creating {user_type} user for {email} using default template")

try:
    # Copy default user template
    new_user = self._copy_default_user(user_type, name, email, password, phone)
    
    # Validate user creation
    if not new_user or not new_user.exists():
        _logger.error(f"User creation from template returned empty recordset for email: {email}")
        return request.make_json_response({
            'success': False,
            'error': 'Failed to create user account. Please try again.'
        }, status=500)
    
    _logger.info(f"User created successfully from template: ID={new_user.id}, login={new_user.login}, active={new_user.active}, groups={new_user.groups_id.mapped('name')}")
    
except Exception as create_error:
    _logger.error(f"Exception during user creation for {email}: {str(create_error)}", exc_info=True)
    return request.make_json_response({
        'success': False,
        'error': f'Failed to create user account: {str(create_error)}'
    }, status=500)
```

## Installation

### Step 1: Update Module

1. Ensure `data/default_users_data.xml` is in place
2. Verify `__manifest__.py` includes the data file:

```python
'data': [
    'security/hr_recruitment_security.xml',
    'security/ir.model.access.xml',
    'security/ir.model.access.csv',
    'data/default_users_data.xml',  # Must be loaded after security
    # ... other data files
],
```

### Step 2: Upgrade Module

```bash
# In Odoo shell or command line
./odoo-bin -u angkot_recruitement -d your_database
```

Or in Odoo web interface:
1. Go to Apps
2. Find "Angkot Recruitment Enhancement"
3. Click "Upgrade"

### Step 3: Verify Default Users

Check that the default users were created:

```python
# In Odoo shell
from odoo import api, SUPERUSER_ID

with api.Environment.manage():
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Find default users (including inactive)
    candidate = env.ref('angkot_recruitement.default_candidate_user')
    employer = env.ref('angkot_recruitement.default_employer_user')
    
    print(f"Candidate Template: {candidate.name} (Active: {candidate.active})")
    print(f"Employer Template: {employer.name} (Active: {employer.active})")
```

## Customization

### Adding Custom Fields to Templates

You can add custom default values to the templates:

```xml
<record id="default_candidate_user" model="res.users">
    <!-- ... existing fields ... -->
    <field name="tz">Asia/Phnom_Penh</field>
    <field name="lang">km_KH</field>
    <field name="signature">Best regards,<br/>Your Name</field>
</record>
```

### Adding Additional Groups

To add more groups to a template:

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

### Modifying Templates at Runtime

Administrators can modify default user templates directly in Odoo:

1. Enable Developer Mode
2. Go to Settings → Users & Companies → Users
3. Remove the "Active" filter
4. Find "Default Candidate Template" or "Default Employer Template"
5. Edit as needed (groups, permissions, default values, etc.)
6. All future user registrations will inherit these changes

## Testing

### Test Default User Creation

```python
# Test script to verify default users exist and are configured correctly
import requests
import json

# Test candidate signup
candidate_data = {
    'name': 'Test Candidate',
    'email': 'test_candidate@example.com',
    'password': 'test123',
    'phone': '012345678',
    'user_type': 'candidate'
}

response = requests.post(
    'http://localhost:8069/api/auth/signup',
    json=candidate_data,
    headers={'Content-Type': 'application/json'}
)

print(f"Candidate signup: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Test employer signup
employer_data = {
    'name': 'Test Employer',
    'email': 'test_employer@example.com',
    'password': 'test123',
    'phone': '098765432',
    'user_type': 'employer'
}

response = requests.post(
    'http://localhost:8069/api/auth/signup',
    json=employer_data,
    headers={'Content-Type': 'application/json'}
)

print(f"Employer signup: {response.status_code}")
print(json.dumps(response.json(), indent=2))
```

### Verify User Groups

After signup, verify that users have correct groups:

```python
# In Odoo shell
user = env['res.users'].search([('login', '=', 'test_candidate@example.com')])
print("Candidate groups:", user.groups_id.mapped('name'))

user = env['res.users'].search([('login', '=', 'test_employer@example.com')])
print("Employer groups:", user.groups_id.mapped('name'))
```

## Troubleshooting

### Issue: Default users not found

**Error**: `Default user template not found: angkot_recruitement.default_candidate_user`

**Solution**:
1. Verify the data file is loaded in `__manifest__.py`
2. Upgrade the module
3. Check Odoo logs for XML parsing errors

### Issue: Users created but missing groups

**Error**: New users don't have expected permissions

**Solution**:
1. Check that default users have correct groups assigned
2. Verify security groups exist before default users are created
3. Ensure `data/default_users_data.xml` is loaded AFTER security files

### Issue: Cannot modify default users

**Error**: Default users are read-only or changes don't persist

**Solution**:
1. Check if `noupdate="1"` is preventing changes
2. To force update during development, use:
```bash
./odoo-bin -u angkot_recruitement -d your_database --init angkot_recruitement
```

### Issue: Template users appear in user lists

**Solution**:
1. Ensure default users have `active="False"`
2. Add domain filter to user views: `[('active', '=', True)]`
3. Template users should only be visible when "Archived" filter is removed

## Security Considerations

1. **Template Security**: Default users are inactive and cannot log in
2. **Login Uniqueness**: Template emails use `.local` domain to avoid conflicts
3. **Password Protection**: Templates don't have usable passwords
4. **Copy Safety**: The `copy()` method creates independent user records
5. **Audit Trail**: All user creation is logged for security auditing

## Migration from Previous Implementation

If upgrading from the old create-from-scratch method:

1. **Backup your database**
2. **Upgrade the module** - this will create default users
3. **Existing users are unaffected** - only new signups use templates
4. **No data migration needed** - existing users keep their settings

## Best Practices

1. **Don't Delete Templates**: Keep default users inactive but don't delete them
2. **Test Changes**: Test template modifications in a staging environment first
3. **Document Customizations**: Keep track of any custom fields or groups added
4. **Regular Audits**: Periodically review template user configurations
5. **Backup Before Changes**: Always backup before modifying templates

## API Response Examples

### Successful Candidate Signup

```json
{
  "success": true,
  "user": {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Your Company",
    "phone": "012345678",
    "role": "job_applicant",
    "groups": [
      {"id": 1, "name": "User types / Internal User"},
      {"id": 50, "name": "Job Applicant"}
    ],
    "permissions": {
      "canApplyJobs": true,
      "canViewApplications": true,
      "canCreateJobs": false,
      "canManageApplicants": false
    },
    "navigation": {
      "showJobs": true,
      "showApplications": true,
      "showApplicants": false,
      "showReports": false
    }
  },
  "message": "Candidate account created successfully",
  "email_verification_required": true,
  "email_sent": true
}
```

### Successful Employer Signup

```json
{
  "success": true,
  "user": {
    "id": 124,
    "name": "Jane Smith",
    "email": "jane@company.com",
    "company": "Your Company",
    "phone": "098765432",
    "role": "recruitment_officer",
    "groups": [
      {"id": 1, "name": "User types / Internal User"},
      {"id": 51, "name": "Recruitment Officer"}
    ],
    "permissions": {
      "canApplyJobs": false,
      "canViewApplications": false,
      "canCreateJobs": true,
      "canManageApplicants": true
    },
    "navigation": {
      "showJobs": true,
      "showApplications": false,
      "showApplicants": true,
      "showReports": true
    }
  },
  "message": "Employer account created successfully",
  "email_verification_required": true,
  "email_sent": true
}
```

## Conclusion

The default user template system provides a robust, maintainable, and flexible approach to user creation in the recruitment module. By centralizing user configuration in template records, it ensures consistency and simplifies administration while maintaining security and performance.

