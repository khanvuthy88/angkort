# Default User Template System - Flow Diagrams

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ODOO DATABASE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │          DEFAULT USER TEMPLATES (Inactive)        │      │
│  ├──────────────────────────────────────────────────┤      │
│  │                                                   │      │
│  │  ┌────────────────────────────────────────┐      │      │
│  │  │  Default Candidate User                │      │      │
│  │  │  - ID: angkot_recruitement.            │      │      │
│  │  │       default_candidate_user           │      │      │
│  │  │  - Login: default_candidate@           │      │      │
│  │  │          template.local                │      │      │
│  │  │  - Active: False                       │      │      │
│  │  │  - Groups:                             │      │      │
│  │  │    • base.group_user                   │      │      │
│  │  │    • group_hr_recruitment_applicant    │      │      │
│  │  └────────────────────────────────────────┘      │      │
│  │                                                   │      │
│  │  ┌────────────────────────────────────────┐      │      │
│  │  │  Default Employer User                 │      │      │
│  │  │  - ID: angkot_recruitement.            │      │      │
│  │  │       default_employer_user            │      │      │
│  │  │  - Login: default_employer@            │      │      │
│  │  │          template.local                │      │      │
│  │  │  - Active: False                       │      │      │
│  │  │  - Groups:                             │      │      │
│  │  │    • base.group_user                   │      │      │
│  │  │    • group_hr_recruitment_officer      │      │      │
│  │  └────────────────────────────────────────┘      │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## User Signup Flow

### Complete Signup Process

```
┌──────────────┐
│ Client App   │
│ (Next.js)    │
└──────┬───────┘
       │
       │ POST /api/auth/signup
       │ {
       │   name: "John Doe",
       │   email: "john@example.com",
       │   password: "pass123",
       │   user_type: "candidate"
       │ }
       │
       ▼
┌────────────────────────────────────────────────────┐
│     Odoo Controller: signup()                      │
├────────────────────────────────────────────────────┤
│                                                    │
│  1. Validate input                                 │
│     ✓ name, email, password present                │
│                                                    │
│  2. Check for existing user                        │
│     ✗ User already exists → Return error          │
│     ✓ New user → Continue                         │
│                                                    │
│  3. Determine role                                 │
│     user_type = "candidate"                        │
│     → role = "job_applicant"                       │
│                                                    │
│  4. Call _copy_default_user()  ────────┐          │
│                                         │          │
└─────────────────────────────────────────┼──────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────┐
│     Method: _copy_default_user(user_type, name, email...)   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Step 1: Find Template                            │      │
│  │                                                   │      │
│  │  user_type = "candidate"                         │      │
│  │  xmlid = "angkot_recruitement.                   │      │
│  │          default_candidate_user"                 │      │
│  │                                                   │      │
│  │  template = env.ref(xmlid)  ──────┐              │      │
│  └──────────────────────────────────┼───────────────┘      │
│                                     │                       │
│  ┌─────────────────────────────────▼────────────────┐      │
│  │ Step 2: Copy Template                            │      │
│  │                                                   │      │
│  │  new_user = template.copy({                      │      │
│  │      'name': 'John Doe',                         │      │
│  │      'login': 'john@example.com',                │      │
│  │      'email': 'john@example.com',                │      │
│  │      'phone': '012345678',                       │      │
│  │      'active': True,                             │      │
│  │      'email_verified': False                     │      │
│  │  })                                              │      │
│  │                                                   │      │
│  │  ┌──────────────────────────────────────┐        │      │
│  │  │  Odoo's copy() automatically:        │        │      │
│  │  │  ✓ Copies all groups                 │        │      │
│  │  │  ✓ Copies company settings           │        │      │
│  │  │  ✓ Copies preferences                │        │      │
│  │  │  ✓ Creates new independent record    │        │      │
│  │  └──────────────────────────────────────┘        │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Step 3: Set Password                             │      │
│  │                                                   │      │
│  │  new_user.write({'password': 'pass123'})         │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Step 4: Return New User                          │      │
│  │                                                   │      │
│  │  return new_user  (ID=123, Active=True)          │      │
│  └────────────────────────┬─────────────────────────┘      │
└─────────────────────────────┼───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│     Back in signup() method                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  5. Validate user creation                                  │
│     ✓ new_user exists                                       │
│                                                             │
│  6. Create candidate profile (if candidate)                 │
│     hr.candidate.create({                                   │
│         'partner_name': 'John Doe',                         │
│         'email_from': 'john@example.com',                   │
│         'user_id': new_user.id                              │
│     })                                                      │
│                                                             │
│  7. Send verification email                                 │
│     new_user.send_verification_email(base_url)              │
│                                                             │
│  8. Build response                                          │
│     user_profile = {                                        │
│         'id': new_user.id,                                  │
│         'name': 'John Doe',                                 │
│         'email': 'john@example.com',                        │
│         'role': 'job_applicant',                            │
│         'groups': [...],                                    │
│         'permissions': {...}                                │
│     }                                                       │
│                                                             │
│  9. Return success response                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Response:
                      │ {
                      │   success: true,
                      │   user: {...},
                      │   email_verification_required: true
                      │ }
                      ▼
               ┌──────────────┐
               │ Client App   │
               │ Shows success│
               └──────────────┘
```

## Comparison: Old vs New Method

### Old Method (Create from Scratch)

```
┌──────────────────────────────────────────────────────┐
│ Manual User Creation (OLD)                           │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. Determine groups based on user_type              │
│     if user_type == 'candidate':                     │
│         group_ids = [                                │
│             (4, ref('base.group_user').id),          │
│             (4, ref('group_applicant').id)           │
│         ]                                            │
│                                                      │
│  2. Build user_vals dictionary                       │
│     user_vals = {                                    │
│         'name': name,                                │
│         'login': email,                              │
│         'email': email,                              │
│         'phone': phone,                              │
│         'groups_id': group_ids,     ← Manual        │
│         'company_id': 1,            ← Manual        │
│         'company_ids': [(4, 1)],    ← Manual        │
│         'active': True,                              │
│         'email_verified': False                      │
│     }                                                │
│                                                      │
│  3. Create user                                      │
│     new_user = env['res.users'].create(user_vals)    │
│                                                      │
│  4. Set password                                     │
│     new_user.write({'password': password})           │
│                                                      │
│  Problems:                                           │
│  ✗ ~70 lines of code                                │
│  ✗ Manual group assignment (error-prone)            │
│  ✗ Hard-coded company IDs                           │
│  ✗ Must maintain group logic in code                │
│  ✗ Changes require code updates                     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### New Method (Copy Template)

```
┌──────────────────────────────────────────────────────┐
│ Template-Based Creation (NEW)                        │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. Get template reference                           │
│     template = env.ref(                              │
│         'angkot_recruitement.default_candidate_user' │
│     )                                                │
│                                                      │
│  2. Copy template with new values                    │
│     new_user = template.copy({                       │
│         'name': name,                                │
│         'login': email,                              │
│         'email': email,                              │
│         'phone': phone,                              │
│         'active': True,                              │
│         'email_verified': False                      │
│     })                                               │
│                                                      │
│     Groups, company, preferences automatically       │
│     inherited from template! ✓                       │
│                                                      │
│  3. Set password                                     │
│     new_user.write({'password': password})           │
│                                                      │
│  Benefits:                                           │
│  ✓ ~20 lines of code (70% reduction)                │
│  ✓ Automatic group inheritance                      │
│  ✓ Consistent configuration                         │
│  ✓ UI-based template management                     │
│  ✓ No code changes for config updates               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Template Inheritance Diagram

```
┌───────────────────────────────────────────────────────┐
│  Default Candidate Template                          │
│  (angkot_recruitement.default_candidate_user)         │
├───────────────────────────────────────────────────────┤
│  Active: False                                        │
│  Login: default_candidate@template.local              │
│  Groups:                                              │
│    • Internal User                                    │
│    • Job Applicant                                    │
│  Company: Main Company                                │
│  Timezone: Asia/Phnom_Penh                           │
│  Language: English                                    │
│  Notification: Email                                  │
└───────────────────┬───────────────────────────────────┘
                    │
                    │ copy()
                    │
    ┌───────────────┼───────────────┬───────────────────┐
    │               │               │                   │
    ▼               ▼               ▼                   ▼
┌────────┐      ┌────────┐      ┌────────┐      ┌─────────┐
│ User 1 │      │ User 2 │      │ User 3 │      │ User N  │
├────────┤      ├────────┤      ├────────┤      ├─────────┤
│Active: │      │Active: │      │Active: │      │Active:  │
│ True   │      │ True   │      │ True   │      │ True    │
│        │      │        │      │        │      │         │
│Inherits│      │Inherits│      │Inherits│      │Inherits │
│all     │      │all     │      │all     │      │all      │
│groups  │      │groups  │      │groups  │      │groups   │
│and     │      │and     │      │and     │      │and      │
│settings│      │settings│      │settings│      │settings │
└────────┘      └────────┘      └────────┘      └─────────┘
```

## Data Flow: Template to User

```
                 TEMPLATE RECORD
┌──────────────────────────────────────────────────┐
│ id: 10                                           │
│ name: "Default Candidate Template"              │
│ login: "default_candidate@template.local"       │
│ active: False                                    │
│ groups_id: [1, 50]  ← Groups inherited          │
│ company_id: 1       ← Company inherited         │
│ tz: "Asia/Phnom_Penh"  ← Timezone inherited    │
│ lang: "en_US"       ← Language inherited        │
│ notification_type: "email" ← Setting inherited  │
└──────────────────────────────────────────────────┘
                        │
                        │ .copy({new values})
                        ▼
                 NEW USER RECORD
┌──────────────────────────────────────────────────┐
│ id: 123  ← New ID assigned                      │
│ name: "John Doe"  ← Override                    │
│ login: "john@example.com"  ← Override           │
│ active: True  ← Override                        │
│ groups_id: [1, 50]  ← Copied from template     │
│ company_id: 1  ← Copied from template          │
│ tz: "Asia/Phnom_Penh"  ← Copied from template  │
│ lang: "en_US"  ← Copied from template          │
│ notification_type: "email" ← Copied from template│
└──────────────────────────────────────────────────┘
```

## Template Management Workflow

```
┌──────────────────────────────────────────────┐
│ Administrator Updates Template               │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ 1. Go to Users Settings    │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ 2. Remove "Active" filter  │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ 3. Find template user          │
    │    "Default Candidate Template"│
    └────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ 4. Edit template               │
    │    - Add/remove groups         │
    │    - Set timezone              │
    │    - Set language              │
    │    - Set signature             │
    │    - Other preferences         │
    └────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ 5. Save changes                │
    └────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────┐
│ All future user signups inherit new settings  │
└────────────────────────────────────────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────────────┐
│                   Security Layers                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Layer 1: Template Inactive                         │
│  ┌───────────────────────────────────────────┐      │
│  │ Templates have active=False               │      │
│  │ Cannot log in or access system            │      │
│  └───────────────────────────────────────────┘      │
│                       │                             │
│                       ▼                             │
│  Layer 2: Unique Login                              │
│  ┌───────────────────────────────────────────┐      │
│  │ Template logins use .local domain         │      │
│  │ No conflict with real user emails         │      │
│  └───────────────────────────────────────────┘      │
│                       │                             │
│                       ▼                             │
│  Layer 3: No Password                               │
│  ┌───────────────────────────────────────────┐      │
│  │ Templates don't have usable passwords     │      │
│  │ Cannot authenticate even if activated     │      │
│  └───────────────────────────────────────────┘      │
│                       │                             │
│                       ▼                             │
│  Layer 4: Copy Creates New Record                   │
│  ┌───────────────────────────────────────────┐      │
│  │ copy() creates independent user           │      │
│  │ No shared state with template             │      │
│  │ Changes to users don't affect template    │      │
│  └───────────────────────────────────────────┘      │
│                       │                             │
│                       ▼                             │
│  Layer 5: Audit Logging                             │
│  ┌───────────────────────────────────────────┐      │
│  │ All operations logged                     │      │
│  │ Template usage tracked                    │      │
│  │ User creation audited                     │      │
│  └───────────────────────────────────────────┘      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Troubleshooting Flow

```
                    User Signup Fails
                           │
                           ▼
            ┌──────────────────────────────┐
            │ Check: Template exists?      │
            └──────┬───────────────────────┘
                   │
        ┌──────────┼──────────┐
        │                     │
     No │                     │ Yes
        ▼                     ▼
┌────────────────┐   ┌──────────────────────┐
│ Run module     │   │ Check: Groups exist? │
│ upgrade        │   └──────┬───────────────┘
└────────────────┘          │
                 ┌──────────┼──────────┐
                 │                     │
              No │                     │ Yes
                 ▼                     ▼
        ┌──────────────┐      ┌──────────────────┐
        │ Load security│      │ Check: Logs show │
        │ data first   │      │ template copy?   │
        └──────────────┘      └──────┬───────────┘
                                     │
                          ┌──────────┼──────────┐
                          │                     │
                       No │                     │ Yes
                          ▼                     ▼
                 ┌──────────────┐      ┌──────────────┐
                 │ Check server │      │ User created │
                 │ logs for     │      │ successfully │
                 │ errors       │      └──────────────┘
                 └──────────────┘
```

---

These diagrams illustrate the complete flow of the default user template system, from architecture to troubleshooting. The template-based approach simplifies user creation while maintaining security and consistency.

