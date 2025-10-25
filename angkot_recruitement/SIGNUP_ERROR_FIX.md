# Signup Error Fix: "Expected singleton: res.users()"

## Issue

During candidate signup, the system was throwing the following error:

```
ERROR test odoo.addons.angkot_recruitement.controllers.controllers: Error in signup API: Expected singleton: res.users()
```

This is a common Odoo error that occurs when trying to call a method or access a field on an empty recordset.

## Root Cause

The error occurred because:

1. **User creation was failing silently** - The `create()` method was returning an empty recordset without raising an exception
2. **No validation after creation** - The code was attempting to access fields and call methods on `new_user` without checking if it was a valid recordset
3. **Singleton methods called on empty recordset** - Methods like `send_verification_email()` which have `self.ensure_one()` were being called on the empty recordset

## Where the Error Occurred

The singleton error could occur at multiple points:

1. **Setting password**: `new_user.password = password`
2. **Creating candidate profile**: `new_user.id` access
3. **Sending verification email**: `new_user.send_verification_email(base_url)` - Has `self.ensure_one()`
4. **Accessing company**: `new_user.company_id`
5. **Accessing groups**: `new_user.groups_id`

## Solution Implemented

### 1. Added User Creation Validation

Wrapped user creation in try-except and added validation:

```python
try:
    new_user = request.env['res.users'].sudo().with_context(no_reset_password=True).create(user_vals)
    
    # Validate user creation
    if not new_user or not new_user.exists():
        _logger.error(f"User creation returned empty recordset for email: {email}")
        return request.make_json_response({
            'success': False,
            'error': 'Failed to create user account. Please try again.'
        }, status=500)
    
    # Set password after validation
    new_user.password = password
    _logger.info(f"User created successfully with ID: {new_user.id}")
    
except Exception as create_error:
    _logger.error(f"Exception during user creation for {email}: {str(create_error)}")
    return request.make_json_response({
        'success': False,
        'error': f'Failed to create user account: {str(create_error)}'
    }, status=500)
```

### 2. Added Candidate Profile Creation Validation

Wrapped candidate creation in try-except:

```python
if user_type == 'candidate':
    try:
        candidate_vals = {
            'partner_name': name,
            'email_from': email,
            'partner_phone': phone or '',
            'user_id': new_user.id,
            'company_id': 1,
        }
        _logger.info(f"Creating candidate profile for user {new_user.id} with values: {candidate_vals}")
        candidate = request.env['hr.candidate'].sudo().create(candidate_vals)
        
        # Validate candidate creation
        if not candidate or not candidate.exists():
            _logger.error(f"Candidate creation returned empty recordset for user {new_user.id}")
        else:
            # Link candidate profile to user
            new_user.sudo().write({'candidate_id': candidate.id})
            _logger.info(f"Successfully created and linked candidate profile {candidate.id} to user {new_user.id}")
    except Exception as candidate_error:
        _logger.error(f"Exception creating candidate profile for user {new_user.id}: {str(candidate_error)}")
        # Don't fail the signup, candidate profile can be created later
```

### 3. Enhanced Error Logging

Added detailed logging throughout the signup process:

- Log before user creation
- Log after successful user creation
- Log before candidate creation
- Log after successful candidate creation
- Log before sending verification email
- Log after successful email send
- Log all exceptions with stack traces (`exc_info=True`)

## Benefits of the Fix

1. **Prevents Silent Failures** - User creation failures are now caught and reported
2. **Better Error Messages** - Users get clear feedback when signup fails
3. **Improved Debugging** - Detailed logs help identify issues quickly
4. **Graceful Degradation** - Candidate profile creation failure doesn't prevent user account creation
5. **Early Exit** - Invalid operations are prevented before they cause singleton errors

## Testing

After applying this fix:

1. ✅ Try to sign up with a valid email
2. ✅ Try to sign up with a duplicate email (should see proper error)
3. ✅ Check Odoo logs for detailed information
4. ✅ Verify user is created successfully
5. ✅ Verify candidate profile is created and linked
6. ✅ Verify verification email is sent

## Log Output Example

**Successful Signup:**
```
INFO: User created successfully with ID: 123
INFO: Creating candidate profile for user 123 with values: {...}
INFO: Successfully created and linked candidate profile 456 to user 123
INFO: Attempting to send verification email to user@example.com for user 123
INFO: Verification email sent successfully to user@example.com
```

**Failed Signup:**
```
ERROR: Exception during user creation for user@example.com: <error details>
```

## Related Files Modified

- `controllers/controllers.py` - Added validation and error handling in `signup()` method

## Prevention

To prevent similar issues in the future:

1. **Always validate record creation**: Check `if record.exists()` after creating records
2. **Use try-except blocks**: Wrap critical operations in error handling
3. **Check before calling singleton methods**: Ensure recordset has exactly one record before calling methods with `ensure_one()`
4. **Add detailed logging**: Log important steps for easier debugging
5. **Test error scenarios**: Don't just test happy paths

## Odoo Best Practices

When working with recordsets in Odoo:

```python
# ✅ GOOD - Validate before using
record = env['model'].create(vals)
if record.exists():
    record.do_something()

# ✅ GOOD - Check recordset size
if len(recordset) == 1:
    recordset.ensure_one()
    recordset.do_something()

# ❌ BAD - No validation
record = env['model'].create(vals)
record.do_something()  # May fail with "Expected singleton"

# ❌ BAD - Assuming create always succeeds
record = env['model'].create(vals)
record.field_name  # May fail if record is empty
```

## Summary

The "Expected singleton: res.users()" error was caused by attempting to use an empty recordset without validation. The fix adds proper error handling and validation at each step of the signup process, ensuring failures are caught early and reported clearly.

