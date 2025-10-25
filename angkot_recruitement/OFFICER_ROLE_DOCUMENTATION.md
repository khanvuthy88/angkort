# Recruitment Roles Documentation

## Overview

Two new roles have been added to the `angkot_recruitement` module to provide different levels of access to job and applicant management functionality:

1. **Recruitment Officer** - Can manage jobs and applicants but are restricted to only see records that are assigned to them
2. **Job Applicant** - Can view job postings and submit applications but cannot create or manage job postings

## Security Groups

### Recruitment Officer Group
**Group Name:** `angkot_recruitement.group_hr_recruitment_officer`  
**Display Name:** "Recruitment Officer"  
**Category:** Human Resources > Recruitment

### Job Applicant Group
**Group Name:** `angkot_recruitement.group_hr_recruitment_applicant`  
**Display Name:** "Job Applicant"  
**Category:** Human Resources > Recruitment

## Permissions

### Recruitment Officer Permissions

#### Job Management (`hr.job`)
- **Read:** ✅ Yes (limited to assigned jobs)
- **Write:** ✅ Yes (limited to assigned jobs)
- **Create:** ✅ Yes
- **Delete:** ❌ No

#### Applicant Management (`hr.applicant`)
- **Read:** ✅ Yes (limited to applicants for assigned jobs)
- **Write:** ✅ Yes (limited to applicants for assigned jobs)
- **Create:** ✅ Yes
- **Delete:** ❌ No

#### Job Category Management (`hr.job.category`)
- **Read:** ✅ Yes (all categories)
- **Write:** ❌ No
- **Create:** ❌ No
- **Delete:** ❌ No

### Job Applicant Permissions

#### Job Management (`hr.job`)
- **Read:** ✅ Yes (active jobs only)
- **Write:** ❌ No
- **Create:** ❌ No
- **Delete:** ❌ No

#### Applicant Management (`hr.applicant`)
- **Read:** ✅ Yes (own applications only)
- **Write:** ✅ Yes (own applications only)
- **Create:** ✅ Yes
- **Delete:** ❌ No

#### Job Category Management (`hr.job.category`)
- **Read:** ✅ Yes (all categories)
- **Write:** ❌ No
- **Create:** ❌ No
- **Delete:** ❌ No

## Record Rules

### Recruitment Officer Record Rules

#### Job Access Rule
**Rule Name:** "Job: Officer Access"  
**Domain:** `['|', ('user_id', '=', user.id), ('user_id', '=', False)]`

Officers can only see:
- Jobs assigned to them (`user_id` = current user)
- Jobs with no assigned user (`user_id` = False)

#### Applicant Access Rule
**Rule Name:** "Applicant: Officer Access"  
**Domain:** `['|', ('job_id.user_id', '=', user.id), ('job_id.user_id', '=', False)]`

Officers can only see:
- Applicants for jobs assigned to them
- Applicants for jobs with no assigned user

#### Job Category Access Rule
**Rule Name:** "Job Category: Officer Access"  
**Domain:** `[(1, '=', 1)]`

Officers can read all job categories (no restrictions).

### Job Applicant Record Rules

#### Job Access Rule
**Rule Name:** "Job: Applicant Access"  
**Domain:** `[('active', '=', True)]`

Applicants can only see:
- Active job postings only
- Cannot see inactive or archived jobs

#### Applicant Access Rule
**Rule Name:** "Applicant: Own Applications Only"  
**Domain:** `[('email_from', '=', user.login)]`

Applicants can only see:
- Their own applications (based on email address)
- Cannot see other applicants' applications

#### Job Category Access Rule
**Rule Name:** "Job Category: Applicant Access"  
**Domain:** `[(1, '=', 1)]`

Applicants can read all job categories (no restrictions).

## How to Use the Roles

### Assigning Jobs to Officers

1. **Via Job Form:**
   - Open any job record
   - Set the "Responsible" field (`user_id`) to the Officer user
   - Save the record

2. **Via Mass Assignment:**
   - Use the list view to select multiple jobs
   - Use the "Action" menu to bulk assign to an Officer

3. **Via API:**
   ```python
   # Assign job to officer
   job = self.env['hr.job'].browse(job_id)
   job.user_id = officer_user_id
   ```

### Setting Up Job Applicants

1. **Create Applicant User:**
   - Create a new user in Odoo
   - Assign the "Job Applicant" group
   - Set appropriate email and login credentials

2. **Applicant Login:**
   - Applicants can log in to view active job postings
   - They can submit applications for jobs
   - They can view their own application history

3. **Via API (Job Portal Integration):**
   ```python
   # Create applicant from job portal
   applicant = self.env['hr.applicant'].create_from_job_portal(
       job_id=job_id,
       application_data={
           'applicant_name': 'John Doe',
           'email': 'john@example.com',
           'phone': '+1234567890',
           'linkedin_url': 'https://linkedin.com/in/johndoe',
           'portfolio_url': 'https://johndoe.com',
           'resume_file': base64_encoded_resume,
           'resume_filename': 'john_doe_resume.pdf'
       }
   )
   ```

## Use Cases

### Recruitment Officer Use Cases

#### Scenario 1: Department-based Recruitment
- Assign different jobs to different Officers based on department
- Each Officer only sees jobs and applicants for their department
- Maintains data privacy and focused workflow

#### Scenario 2: Geographic Recruitment
- Assign jobs by location to specific Officers
- Officers manage recruitment for their assigned regions
- Prevents cross-region data access

#### Scenario 3: Role-based Recruitment
- Assign technical jobs to technical Officers
- Assign administrative jobs to administrative Officers
- Specialized handling based on job requirements

### Job Applicant Use Cases

#### Scenario 1: Job Portal Integration
- Applicants can browse and search active job postings
- Submit applications directly through the portal
- Track their application status and history

#### Scenario 2: Self-Service Application Management
- Applicants can update their application details
- View application status and feedback
- Upload additional documents or portfolios

#### Scenario 3: External Job Board Integration
- Allow external job seekers to apply without full Odoo access
- Maintain application data within the system
- Enable automated application processing

### 📋 **Permissions Summary:**

#### Recruitment Officer Permissions
| Model | Read | Write | Create | Delete |
|-------|------|-------|--------|--------|
| Jobs | ✅ (assigned only) | ✅ (assigned only) | ✅ | ❌ |
| Applicants | ✅ (assigned jobs only) | ✅ (assigned jobs only) | ✅ | ❌ |
| Job Categories | ✅ (all) | ❌ | ❌ | ❌ |

#### Job Applicant Permissions
| Model | Read | Write | Create | Delete |
|-------|------|-------|--------|--------|
| Jobs | ✅ (active only) | ❌ | ❌ | ❌ |
| Applicants | ✅ (own only) | ✅ (own only) | ✅ | ❌ |
| Job Categories | ✅ (all) | ❌ | ❌ | ❌ |

## Security Benefits

1. **Data Isolation:** Officers only see relevant records
2. **Focused Workflow:** Reduces information overload
3. **Compliance:** Maintains data privacy requirements
4. **Scalability:** Easy to add/remove Officers without affecting others
5. **Audit Trail:** Clear assignment of responsibility

## Migration Notes

When upgrading to this version:

1. **Existing Users:** No automatic assignment - jobs must be manually assigned
2. **Unassigned Jobs:** Officers can see jobs with no assigned user
3. **Data Integrity:** All existing data remains accessible to managers
4. **Backward Compatibility:** Manager roles retain full access

## Technical Implementation

### Files Modified/Created:
- `security/hr_recruitment_security.xml` - Group definitions and record rules for both roles
- `security/ir.model.access.xml` - Access rights for both Officer and Applicant groups
- `security/ir.model.access.csv` - CSV access rights for both groups
- `__manifest__.py` - Updated to include new security file
- `OFFICER_ROLE_DOCUMENTATION.md` - Comprehensive documentation

### Key Components:
- **Security Groups:** 
  - `group_hr_recruitment_officer` - For recruitment officers
  - `group_hr_recruitment_applicant` - For job applicants
- **Record Rules:** Domain-based filtering for job and applicant access
- **Access Rights:** Read/Write/Create permissions (no delete for both roles)
- **Integration:** Works with existing Odoo security framework

## Testing

### Testing the Recruitment Officer Role:

1. Create a test user
2. Assign the "Recruitment Officer" group
3. Create jobs and assign some to the Officer
4. Verify the Officer can only see assigned jobs
5. Verify the Officer can only see applicants for assigned jobs
6. Test create/edit permissions on assigned records

### Testing the Job Applicant Role:

1. Create a test user
2. Assign the "Job Applicant" group
3. Create some active and inactive jobs
4. Verify the Applicant can only see active jobs
5. Create applications as the Applicant user
6. Verify the Applicant can only see their own applications
7. Test that the Applicant cannot create or edit jobs

## Support

For questions or issues with the Officer role implementation, refer to the Odoo documentation on security groups and record rules, or contact the development team.
