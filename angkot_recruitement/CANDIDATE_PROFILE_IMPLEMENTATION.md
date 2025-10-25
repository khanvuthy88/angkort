# Candidate Profile Enhancement - Implementation Guide

## Overview

This document describes the implementation of comprehensive candidate profile management features in the `angkot_recruitement` Odoo module. These features mirror the functionality implemented in the Next.js frontend, allowing candidates to build complete professional profiles.

## New Models

### 1. `hr.candidate.education` - Education History

Stores candidate's educational background with support for multiple education entries.

**Key Fields:**
- `school`: Educational institution name (required)
- `degree`: Degree type (selection field with common degrees)
- `field_of_study`: Major or area of study
- `start_date`, `end_date`: Education period
- `is_current`: Flag for ongoing education
- `description`: Additional details (GPA, honors, coursework)
- `gpa`: Grade Point Average
- `duration_display`: Computed human-readable duration

**Features:**
- Date validation (end date must be after start date)
- Automatic duration calculation and display
- Support for current/ongoing education

---

### 2. `hr.candidate.experience` - Work Experience

Tracks professional work history with detailed employment information.

**Key Fields:**
- `company`: Company name (required)
- `position`: Job title (required)
- `location`: Work location
- `employment_type`: Type of employment (full-time, part-time, contract, etc.)
- `start_date`, `end_date`: Employment period
- `is_current`: Flag for current position
- `description`: Job responsibilities and role details (required)
- `achievements`: Key accomplishments and results
- `duration_months`: Computed total duration in months
- `duration_display`: Human-readable duration

**Features:**
- Automatic calculation of work duration in months
- Support for current employment
- Tracks total professional experience
- Formatted display of employment period

---

### 3. `hr.candidate.certification` - Professional Certifications

Manages professional certifications with expiration tracking.

**Key Fields:**
- `name`: Certification name (required)
- `issuer`: Issuing organization (required)
- `credential_id`: Unique credential identifier
- `credential_url`: Verification URL
- `issue_date`: When certification was issued (required)
- `expiry_date`: Expiration date (optional)
- `is_expired`: Computed expiration status
- `is_expiring_soon`: Computed flag for certifications expiring within 90 days
- `status_display`: Human-readable status

**Features:**
- Automatic expiration tracking
- Warning for certifications expiring soon (within 90 days)
- Direct link to credential verification
- Visual indicators for expired/expiring certifications
- Date validation

---

### 4. `hr.candidate.portfolio` - Portfolio Projects

Showcases candidate's projects and work samples.

**Key Fields:**
- `title`: Project name (required)
- `description`: Project details and role (required)
- `url`: Project URL (GitHub, live demo, etc.) (required)
- `image`: Stored project image/screenshot
- `image_url`: External image URL
- `sequence`: Display order
- `project_type`: Type of project (web, mobile, desktop, etc.)
- `status`: Project status (completed, ongoing, maintenance, archived)
- `tag_ids`: Many2many relation to technology tags
- `start_date`, `end_date`: Project timeline
- `url_domain`: Computed domain from URL

**Features:**
- Drag-and-drop ordering via sequence
- Support for technology/skill tags
- Multiple views (tree, kanban, form)
- Automatic URL parsing
- Direct link to view project
- Image support (stored or external URL)

---

### 5. `hr.candidate.portfolio.tag` - Technology Tags

Manages technology and skill tags for portfolio projects.

**Key Fields:**
- `name`: Technology name (unique)
- `color`: Color index for visual representation

**Features:**
- Reusable across multiple projects
- Color-coded display
- Unique constraint on tag names

---

## Extended `hr.candidate` Model

The `hr.candidate` model has been extended with the following fields:

**One2many Relations:**
- `education_ids`: Link to education entries
- `experience_ids`: Link to work experiences
- `certification_ids`: Link to certifications
- `portfolio_ids`: Link to portfolio projects

**Computed Fields:**
- `education_count`: Number of education entries
- `experience_count`: Number of work experiences
- `certification_count`: Number of certifications
- `portfolio_count`: Number of portfolio projects
- `total_experience_months`: Total professional experience in months

---

## User Interface Enhancements

### Smart Buttons

Four smart buttons added to candidate form view:
1. **Education** (📚) - Quick access to education records
2. **Experience** (💼) - Quick access to work experience
3. **Certifications** (🏆) - Quick access to certifications
4. **Portfolio** (💻) - Quick access to portfolio projects

Each button displays the count of related records.

### Notebook Tabs

Four new tabs added to candidate form:

#### 1. Education Tab
- List view showing school, degree, field, duration
- Inline form for adding/editing education
- "Currently studying" checkbox

#### 2. Experience Tab
- Shows total experience in months at the top
- List view with position, company, employment type, duration
- Inline form for adding/editing experience
- "Currently working" checkbox
- Separate fields for job description and achievements

#### 3. Certifications Tab
- Visual indicators for expired/expiring certifications
- Red text for expired certifications
- Orange text for expiring soon (within 90 days)
- "Verify" button to open credential URL
- Status display (Active, Expired, Expiring in X days, No Expiration)

#### 4. Portfolio Tab
- Drag-and-drop reordering
- Kanban and tree views available
- Project image display
- Technology tags with colors
- "View Project" button to open project URL
- Project type and status indicators

---

## Security & Access Rights

All new models have comprehensive access rights for:
- **Public users**: Read-only access
- **Internal users**: Read, Write, Create (limited delete)
- **Recruitment Manager**: Full access
- **Recruitment Officer**: Full access except delete
- **Job Applicants**: Full access to manage their own profiles

### Access Rights Summary

| Model | Public | User | Manager | Officer | Applicant |
|-------|--------|------|---------|---------|-----------|
| hr.candidate.education | R | RWC | RWCD | RWCD | RWCD |
| hr.candidate.experience | R | RWC | RWCD | RWCD | RWCD |
| hr.candidate.certification | R | RWC | RWCD | RWCD | RWCD |
| hr.candidate.portfolio | R | RWC | RWCD | RWCD | RWCD |
| hr.candidate.portfolio.tag | R | RWC | RWCD | RWCD | RWCD |

---

## Technical Implementation Details

### Date Handling
- All date fields use Odoo's `Date` field type
- Automatic validation ensures end dates are after start dates
- Support for ongoing/current entries (education, experience)
- Formatted date displays (e.g., "Jan 2020 - Dec 2023")

### Duration Calculations
- Education and Experience models compute duration automatically
- Duration displayed in human-readable format
- Experience duration tracked in months for analytics
- Uses `dateutil.relativedelta` for accurate month calculations

### Computed Fields
- All computed fields are stored for performance
- Automatic recalculation when dependent fields change
- Proper dependency decorators (`@api.depends`)

### Validation
- Constraint methods prevent invalid data entry
- Custom validation messages for user-friendly errors
- URL validation with automatic protocol addition

### Views
- Responsive forms with grouped fields
- Tree views optimized for list display
- Kanban view for visual portfolio browsing
- Inline editing support in One2many fields
- Context passing for default values

---

## Integration with Next.js Frontend

The Odoo models are designed to seamlessly integrate with the Next.js frontend:

### Data Structure Alignment
- Field names and types match Next.js TypeScript interfaces
- Selection field values compatible with frontend enums
- Date formats easily serializable to ISO format
- Computed fields provide ready-to-use display values

### API Endpoints
The models can be accessed through Odoo's JSON-RPC API:

```python
# Example: Fetch candidate profile with all related data
/web/dataset/call_kw/hr.candidate/read
{
    "ids": [candidate_id],
    "fields": [
        "education_ids",
        "experience_ids", 
        "certification_ids",
        "portfolio_ids",
        "total_experience_months"
    ]
}
```

### Recommended API Calls
1. **Get Profile Data**: Read candidate with nested relations
2. **Create Entry**: Create education/experience/certification/portfolio
3. **Update Entry**: Write to specific record
4. **Delete Entry**: Unlink specific record
5. **Reorder Portfolio**: Write sequence field for drag-and-drop

---

## Installation & Upgrade

### Installation Steps
1. Ensure all dependencies are installed (base, hr, hr_recruitment)
2. Place module in addons path
3. Update module list
4. Install `angkot_recruitement` module

### Upgrade Existing Installation
If upgrading from a previous version:

```bash
# Upgrade the module
odoo-bin -u angkot_recruitement -d your_database
```

The new models will be automatically created with:
- Database tables
- Security groups
- Access rights
- Views and actions

---

## Usage Examples

### For Recruiters/Officers

1. **View Candidate Profile**
   - Open candidate form
   - Use smart buttons to quickly access profile sections
   - View aggregated data (total experience months)

2. **Assess Candidate Qualifications**
   - Review education background in Education tab
   - Check work history and achievements in Experience tab
   - Verify certifications (including expiration status)
   - Browse portfolio projects with visual previews

3. **Add Profile Information**
   - Use inline forms to add missing information
   - Add certifications from interviews
   - Document portfolio projects discussed

### For Applicants (via Frontend)

1. **Build Complete Profile**
   - Add multiple education entries
   - Document all work experiences
   - Upload certifications with verification links
   - Showcase projects with images and tech stacks

2. **Manage Certifications**
   - Track certification expiration dates
   - Get warnings for expiring certifications
   - Maintain verification URLs

3. **Organize Portfolio**
   - Drag-and-drop to reorder projects
   - Add technology tags for better categorization
   - Include live demos and GitHub links

---

## Best Practices

### Data Entry
1. **Completeness**: Encourage candidates to fill all fields
2. **Accuracy**: Verify dates and details
3. **Evidence**: Use credential URLs and project links when available
4. **Consistency**: Use standard formats for company names, degrees, etc.

### Maintenance
1. **Regular Updates**: Remind candidates to update expiring certifications
2. **Portfolio Refresh**: Keep portfolio projects current and relevant
3. **Experience Updates**: Add new positions and achievements
4. **Data Cleanup**: Archive outdated or irrelevant entries

### Performance
1. **Indexed Fields**: candidate_id fields are indexed for fast queries
2. **Computed Storage**: Stored computed fields reduce calculation overhead
3. **Lazy Loading**: Use appropriate views to load only necessary data

---

## Future Enhancements

Potential improvements for future versions:

1. **Skills Management**: Separate skills model linked to both experience and education
2. **Endorsements**: Allow verification of skills by others
3. **Document Attachments**: Direct file uploads per entry
4. **Timeline View**: Visual timeline of education and experience
5. **AI Integration**: Auto-suggest skills based on experience
6. **Social Media Integration**: Pull data from LinkedIn, GitHub
7. **Resume Generation**: Auto-generate resume from profile data
8. **Profile Completeness Score**: Calculate and display profile completion percentage
9. **Recommendations**: System to provide recommendations/endorsements
10. **Portfolio Analytics**: Track views and engagement on portfolio projects

---

## Troubleshooting

### Common Issues

**Issue**: Smart buttons not showing
- **Solution**: Ensure actions are defined in XML and views are loaded

**Issue**: Computed fields not updating
- **Solution**: Check `@api.depends` decorators include all dependencies

**Issue**: Access rights errors
- **Solution**: Verify ir.model.access.csv includes entries for all models

**Issue**: Views not displaying correctly
- **Solution**: Check XML syntax and field names match model definitions

---

## API Integration Examples

### Fetch Candidate Profile (Python/Odoo RPC)
```python
import odoorpc

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('dbname', 'username', 'password')

Candidate = odoo.env['hr.candidate']
candidate = Candidate.browse(candidate_id)

# Get all profile data
profile = {
    'name': candidate.partner_name,
    'email': candidate.email_from,
    'education': [
        {
            'id': edu.id,
            'school': edu.school,
            'degree': edu.degree,
            'field': edu.field_of_study,
            'startDate': edu.start_date.isoformat() if edu.start_date else None,
            'endDate': edu.end_date.isoformat() if edu.end_date else None,
            'current': edu.is_current,
            'description': edu.description,
        }
        for edu in candidate.education_ids
    ],
    'experience': [
        {
            'id': exp.id,
            'company': exp.company,
            'position': exp.position,
            'location': exp.location,
            'employmentType': exp.employment_type,
            'startDate': exp.start_date.isoformat(),
            'endDate': exp.end_date.isoformat() if exp.end_date else None,
            'current': exp.is_current,
            'description': exp.description,
            'achievements': exp.achievements,
        }
        for exp in candidate.experience_ids
    ],
    'certifications': [
        {
            'id': cert.id,
            'name': cert.name,
            'issuer': cert.issuer,
            'credentialId': cert.credential_id,
            'credentialUrl': cert.credential_url,
            'issueDate': cert.issue_date.isoformat(),
            'expiryDate': cert.expiry_date.isoformat() if cert.expiry_date else None,
            'status': cert.status_display,
        }
        for cert in candidate.certification_ids
    ],
    'portfolio': [
        {
            'id': port.id,
            'title': port.title,
            'description': port.description,
            'url': port.url,
            'imageUrl': port.image_url,
            'projectType': port.project_type,
            'status': port.status,
            'tags': [tag.name for tag in port.tag_ids],
        }
        for port in candidate.portfolio_ids
    ],
    'totalExperience': candidate.total_experience_months,
}
```

### Create Education Entry (JavaScript/JSON-RPC)
```javascript
const response = await fetch('/web/dataset/call_kw/hr.candidate.education/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'call',
    params: {
      model: 'hr.candidate.education',
      method: 'create',
      args: [{
        candidate_id: candidateId,
        school: 'Stanford University',
        degree: 'bachelor_science',
        field_of_study: 'Computer Science',
        start_date: '2016-09-01',
        end_date: '2020-06-01',
        is_current: false,
        description: 'Focused on AI and Machine Learning. GPA: 3.8/4.0',
      }],
      kwargs: {},
    },
  }),
});
```

---

## Conclusion

This implementation provides a comprehensive candidate profile management system that:
- ✅ Stores complete professional profiles
- ✅ Tracks education, experience, certifications, and portfolio
- ✅ Provides intuitive UI for data entry and viewing
- ✅ Includes smart validations and computed fields
- ✅ Integrates seamlessly with Next.js frontend
- ✅ Supports role-based access control
- ✅ Enables data-driven candidate assessment

The models are production-ready and follow Odoo best practices for performance, security, and maintainability.

---

## Support & Documentation

For questions or issues:
1. Check this documentation
2. Review Odoo logs for errors
3. Verify XML views syntax
4. Check security access rights
5. Test with sample data first

## Version History

- **v1.0** (2025-10-12): Initial implementation of candidate profile models
  - Education, Experience, Certification, Portfolio models
  - UI enhancements with smart buttons and tabs
  - Complete access rights configuration
  - Integration-ready for Next.js frontend

