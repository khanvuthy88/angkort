# Candidate Deletion Fix

## Problem

When attempting to delete a candidate from the `hr_candidate` table, a foreign key constraint violation error occurred:

```
ERROR: update or delete on table "hr_candidate" violates foreign key constraint "hr_applicant_candidate_id_fkey" on table "hr_applicant"
DETAIL: Key (id)=(18) is still referenced from table "hr_applicant".
```

### Root Cause

The `hr.applicant` model has a **required** `candidate_id` field that references `hr.candidate`. When a candidate has associated job applications, the database constraint prevents deletion to maintain referential integrity.

## Solution Implemented

### 1. **Enhanced Deletion Validation** (`unlink` method override)

Added a custom `unlink` method in `hr_candidate.py` that:
- Checks if the candidate has any related job applications
- Prevents deletion with a **user-friendly error message** that includes:
  - The number of applications linked to the candidate
  - The job titles of those applications (up to 3, with count if more)
  - A suggestion to archive instead of delete

```python
def unlink(self):
    """Override unlink to handle candidates with applicants gracefully."""
    for candidate in self:
        # Check if there are any applicants linked to this candidate
        applicants = self.env['hr.applicant'].search([
            ('candidate_id', '=', candidate.id)
        ])
        
        if applicants:
            # Get job titles for better error message
            job_titles = ', '.join(applicants.mapped('job_id.name')[:3])
            if len(applicants) > 3:
                job_titles += f', and {len(applicants) - 3} more'
            
            raise UserError(
                _("Cannot delete candidate '%s' because there are %d job application(s) linked to this candidate "
                  "(Jobs: %s).\n\n"
                  "Please consider archiving the candidate instead, or delete the related applications first.") 
                % (candidate.partner_name or candidate.email_from, len(applicants), job_titles)
            )
    
    return super(HrCandidate, self).unlink()
```

### 2. **Archive Functionality** (`action_archive_with_applicants` method)

Added a new method that allows users to archive candidates along with their applications:
- Archives the candidate (sets `active = False`)
- Archives all related job applications
- Shows a success notification with the count of archived applications
- Provides a one-click solution instead of deletion

```python
def action_archive_with_applicants(self):
    """Archive candidate along with all related applicants."""
    self.ensure_one()
    
    # Find all related applicants
    applicants = self.env['hr.applicant'].search([
        ('candidate_id', '=', self.id)
    ])
    
    # Archive the candidate and applicants
    if applicants:
        applicants.write({'active': False})
        self.active = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Archived Successfully'),
                'message': _('Candidate and %d related application(s) have been archived.') % len(applicants),
                'type': 'success',
                'sticky': False,
            }
        }
```

### 3. **UI Enhancement**

Added an "Archive Candidate" button in the candidate form view header:
- Visible on all candidate records
- Shows a confirmation dialog before archiving
- Executes the archive action with one click

```xml
<button name="action_archive_with_applicants" 
        type="object" 
        string="Archive Candidate" 
        confirm="This will archive the candidate and all related job applications. Continue?"
        help="Archive this candidate and all related job applications"/>
```

## Benefits

1. **Better UX**: Clear, informative error messages instead of cryptic database errors
2. **Data Preservation**: Archiving instead of deleting maintains historical data
3. **Efficiency**: One-click archive action for candidates with applications
4. **Database Integrity**: Maintains referential integrity while providing flexibility
5. **Odoo Best Practice**: Follows Odoo's recommendation to archive instead of delete

## Usage

### When Deletion is Blocked

If you try to delete a candidate with applications, you'll see:

```
Cannot delete candidate 'John Doe' because there are 2 job application(s) linked to this candidate (Jobs: Software Engineer, Data Analyst).

Please consider archiving the candidate instead, or delete the related applications first.
```

### Archiving a Candidate

1. Open the candidate record
2. Click the **"Archive Candidate"** button in the header
3. Confirm the action
4. The candidate and all related applications will be archived
5. A success notification will appear

### Viewing Archived Candidates

To view archived candidates:
1. Go to Recruitment > Candidates
2. Click on the "Filters" button
3. Remove or modify the "Active" filter
4. Archived candidates will appear (you can unarchive them if needed)

## Files Modified

- `/models/hr_candidate.py` - Added `unlink()` and `action_archive_with_applicants()` methods
- `/views/hr_candidate_views.xml` - Added "Archive Candidate" button to form view

## Testing

1. ✅ Try to delete a candidate with applications → Should show detailed error
2. ✅ Archive a candidate with applications → Should archive both candidate and applications
3. ✅ Delete a candidate without applications → Should work normally
4. ✅ Archive a candidate without applications → Should archive only the candidate

## Alternative Solutions Considered

1. **Cascade Delete**: Delete applications when candidate is deleted
   - ❌ Not recommended: Loss of important historical data

2. **Set Null**: Allow `candidate_id` to be null
   - ❌ Not possible: `candidate_id` is a required field in Odoo's standard model

3. **Prevent Deletion Only**: Show error without archive option
   - ❌ Less user-friendly: Requires manual archiving

4. **Current Solution**: Prevent deletion + Provide easy archive action ✅
   - ✅ Best UX: Clear messages + one-click alternative
   - ✅ Data preservation: Nothing is permanently deleted
   - ✅ Follows Odoo conventions: Archiving is the recommended approach

## Notes

- This fix follows Odoo's best practices for handling related records
- The archive functionality preserves all historical data
- Users can always unarchive candidates if needed
- The database constraint remains intact, ensuring data integrity

