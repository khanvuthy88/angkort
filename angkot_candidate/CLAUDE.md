# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module Overview

`angkot_candidate` is an Odoo 18 module for candidate onboarding. It extends `hr.candidate` (from `hr_recruitment`) with:
- A multi-section employee information form (personal, family, spouse, education, employment, etc.)
- A document checklist where candidates upload PDFs/images and HR reviews them
- A portal UI at `/my/candidate/documents` for portal-auth uploads
- A REST API at `/angkort/api/v1/` for JWT-authenticated front-end clients

## Running Tests

```bash
# Run all module tests
odoo-bin -d <database> --test-enable --test-tags=angkot_candidate -i angkot_candidate

# Run a single test method
odoo-bin -d <database> --test-enable --test-tags=/angkot_candidate:TestCandidateApi.test_login_returns_candidate_role_enum

# Import Postman collection for manual API testing
# postman/Angkot_Candidate_API.postman_collection.json
# postman/Angkot_Candidate_API.postman_environment.json
```

Tests use `@tagged("-at_install", "post_install")` and extend `HttpCase`. The `database.secret` system parameter must be set for JWT to work.

## Architecture

### API Layer (`controllers/api.py`)

All routes are under `/angkort/api/v1/`. There is a single controller class `CandidateDocumentApi` that handles everything. Routes use `auth="none"` or `auth="public"` — authentication is done manually inside each handler via `_get_authenticated_user()`, which checks the Odoo session first, then falls back to `Bearer` JWT token validation.

**JWT auth:** Tokens are issued by `_issue_tokens()` and stored in `res.user.token` if the `e_menu` module is installed (graceful fallback if not). The `_get_bearer_user()` method validates the token signature and optionally checks DB-side revocation.

**Response envelope:**
```json
{"status": "success", "message": "...", "data": {...}}
{"status": "error", "message": "...", "statusCode": 400, "errors": [...]}
```

**Key API routes:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/login` | Authenticate and issue JWT tokens |
| POST | `/refresh` | Rotate tokens with a refresh token |
| GET/POST | `/candidate/employee-form` | Current user's employee form (no ID) |
| GET/POST | `/candidates/<id>/employee-form` | Specific candidate's employee form |
| POST | `/candidates/<id>/employee-form/submit` | Candidate submits form for review |
| POST | `/candidates/<id>/employee-form/approve` | HR approves submitted form |
| POST | `/candidates/<id>/employee-form/reject` | HR rejects submitted form |
| POST | `/candidates/<id>/employee-form/withdraw` | HR withdraws a review decision |
| GET | `/candidates` | List candidates visible to current user |
| GET | `/candidates/<id>` | Get single candidate basic info |
| GET | `/candidate/documents` | List current user's document checklist |
| POST | `/candidate/documents/<id>/upload` | Upload a file for a document line |
| DELETE | `/candidate/documents/<id>` | Remove an uploaded file |
| POST | `/candidate/documents/<id>/review` | Review a document (accept/reject) |

### Portal Layer (`controllers/portal.py`)

Extends `CustomerPortal` for session-based (non-API) access. Routes:
- `GET /my/candidate/documents` — view checklist
- `POST /my/candidate/documents/<id>/upload` — upload file, redirects back with flash message
- `GET /my/candidate/documents/<id>/content` — stream attachment inline

### Data Model

**`hr.candidate` extension (`models/hr_candidate.py`):**
- `candidate_stage`: `draft → submitted → accepted/rejected`
- `portal_user_id`: portal user linked to this candidate (the "owner")
- `officer_user_id`: encharge officer assigned to oversee this candidate
- `document_ids`: one-to-many to `angkot.candidate.document`
- `_ensure_required_document_lines()`: auto-creates document checklist lines for all active document types whenever a candidate is created or its `portal_user_id`/`company_id` changes
- `english_name` and `partner_name` are kept in sync on write/create

**`angkot.candidate.document` (`models/candidate_document.py`):**
- Unique per `(candidate_id, document_type_id)` — one checklist line per document type per candidate
- `status`: `missing → submitted → accepted/rejected`
- `portal_upload_file()`: validates MIME type (PDF, JPEG, PNG, WebP, GIF, BMP, TIFF), replaces attachment, posts to chatter
- Deleting a document record also unlinks its `ir.attachment`

**`angkot.candidate.document.type` (`models/candidate_document.py`):**
- Seeded in `data/candidate_document_type_data.xml` (`noupdate="1"`)
- Categories: `identity`, `education`, `banking`, `compliance`, `other`
- Code must be globally unique (SQL constraint)

### Security Groups

Groups are defined in `security/security.xml` with an inheritance chain:

```
group_candidate_portal (→ base.group_portal)
  └── group_candidate_general_staff
  └── group_candidate_finance_staff

group_candidate_encharge_officer (→ hr_recruitment interviewer)
  └── group_candidate_recruiter

group_candidate_hr_reviewer (→ hr_recruitment user)
  └── group_candidate_hr
```

**Access matrix for the API (enforced in controller, not just ORM rules):**

| Action | Candidate | General/Finance Staff | Encharge Officer | Recruiter | HR Reviewer | HR |
|---|---|---|---|---|---|---|
| View own employee form | own | own | assigned | assigned | all | all |
| Edit employee form | own (all fields) | own (filtered fields) | assigned | assigned | all | all |
| Submit form | own | — | — | — | — | — |
| Approve/reject form | — | — | — | — | — | all |
| Withdraw form review | — | — | — | — | — | all |
| Upload document | own | own | — | assigned | all | all |
| Delete document upload | own (staff only) | own | — | assigned | — | all |
| Review document | — | — | assigned | assigned | all | all |

**Finance staff** can only edit personal info + `guarantee_letter` + `conflict_interest` fields; their serialized response excludes family/spouse/education sections.  
**General staff** can only edit personal info + `conflict_interest` fields; their serialized response excludes family/spouse/education/guaranteeLetter sections.

`res.users.candidate_role` is a computed/inverse field that maps these groups to a friendly selection for the user form UI.