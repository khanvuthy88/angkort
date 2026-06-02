# Angkot Candidate User Test Cases

## Scope

These test cases cover candidate onboarding API behavior for these roles:

- Candidate
- Candidate (General staff)
- Candidate (Finance staff)
- Recruiter
- HR

Base API URL:

```text
/angkort/api/v1
```

Employee form route:

```text
/angkort/api/v1/candidates/<candidate_id>/employee-form
/angkort/api/v1/candidates/<candidate_id>/employee-form/submit
/angkort/api/v1/candidates/<candidate_id>/employee-form/approve
/angkort/api/v1/candidates/<candidate_id>/employee-form/reject
```

Document routes:

```text
/angkort/api/v1/candidate/documents
/angkort/api/v1/candidate/documents/<document_id>/upload
/angkort/api/v1/candidate/documents/<document_id>
/angkort/api/v1/candidate/documents/<document_id>/review
/angkort/api/v1/candidate/documents/<document_id>/accept
/angkort/api/v1/candidate/documents/<document_id>/reject
/angkort/api/v1/candidate/documents/<document_id>/content
```

## Preconditions

- The `angkot_candidate` module is installed.
- Candidate document types are loaded.
- Each test user has a linked `hr.candidate` record where required.
- Recruiter test user is assigned as `officer_user_id` on at least one candidate.
- HR test user has the `HR` role.
- API authentication returns a valid bearer token.

## TC-01 Login Returns Candidate Role

Role: Candidate

Steps:

1. Login with a normal candidate portal user.
2. Check the response payload.

Expected result:

- Login succeeds.
- Response role is `candidate`.

## TC-02 Login Returns General Staff Role

Role: Candidate (General staff)

Steps:

1. Login with a Candidate (General staff) user.
2. Check the response payload.

Expected result:

- Login succeeds.
- Response role is `candidate_general_staff`.

## TC-03 Login Returns Finance Staff Role

Role: Candidate (Finance staff)

Steps:

1. Login with a Candidate (Finance staff) user.
2. Check the response payload.

Expected result:

- Login succeeds.
- Response role is `candidate_finance_staff`.

## TC-04 Login Returns Recruiter Role

Role: Recruiter

Steps:

1. Login with a Recruiter user.
2. Check the response payload.

Expected result:

- Login succeeds.
- Response role is `recruiter`.

## TC-05 Login Returns HR Role

Role: HR

Steps:

1. Login with an HR user.
2. Check the response payload.

Expected result:

- Login succeeds.
- Response role is `hr`.

## TC-06 Candidate Updates Full Employee Form

Role: Candidate

Steps:

1. Login as a candidate.
2. Send `POST` or `PUT` to `/candidates/<own_candidate_id>/employee-form`.
3. Include all sections:
   - `personalInformation`
   - `familyInformation`
   - `spouseInformation`
   - `educationInformation`
   - `shortCourseInformation`
   - `employmentHistory`
   - `otherInformation`
   - `declaration`
4. Fetch the same form again.

Expected result:

- Save succeeds.
- All submitted editable sections are stored.
- Response includes all employee form sections.

## TC-07 Old Employee Form Route Is Removed

Role: Any authenticated role

Steps:

1. Login as any user.
2. Send `GET` to `/candidate/employee-form`.

Expected result:

- Route is not available.
- Response status is `404`.
- Users must use `/candidates/<candidate_id>/employee-form`.

## TC-08 Employee Form Accepts Nuxt Field Names

Role: Candidate

Steps:

1. Login as a candidate.
2. Send `POST` or `PUT` to `/candidates/<own_candidate_id>/employee-form`.
3. Use frontend field names such as:
   - `nationalId`
   - `fatherOccupation`
   - `motherOccupation`
   - `spouseName`
   - `occupation`
   - `duration`
   - `certificates`
   - `responsible`
   - `illness`
   - `illnessOther`
   - `crime`
   - `crimeOther`
4. Fetch the form again.

Expected result:

- Save succeeds.
- Nuxt field names map to the correct Odoo fields.
- Section-specific fields such as `duration` map correctly based on section.

## TC-09 General Staff Updates Allowed Form Sections Only

Role: Candidate (General staff)

Steps:

1. Login as Candidate (General staff).
2. Send `POST` or `PUT` to `/candidates/<own_candidate_id>/employee-form`.
3. Include:
   - `personalInformation`
   - `conflictInterest`
   - `familyInformation`
   - `guaranteeLetter`
4. Fetch the form again.

Expected result:

- Save succeeds.
- `personalInformation` is saved.
- `conflictInterest` is saved.
- `familyInformation` is not saved.
- `guaranteeLetter` is not saved.
- Response includes only:
  - `candidateId`
  - `candidateName`
  - `personalInformation`
  - `conflictInterest`

## TC-10 Finance Staff Updates Allowed Form Sections Only

Role: Candidate (Finance staff)

Steps:

1. Login as Candidate (Finance staff).
2. Send `POST` or `PUT` to `/candidates/<own_candidate_id>/employee-form`.
3. Include:
   - `personalInformation`
   - `guaranteeLetter`
   - `conflictInterest`
   - `familyInformation`
4. Fetch the form again.

Expected result:

- Save succeeds.
- `personalInformation` is saved.
- `guaranteeLetter` is saved.
- `conflictInterest` is saved.
- `familyInformation` is not saved.
- Response includes only:
  - `candidateId`
  - `candidateName`
  - `personalInformation`
  - `guaranteeLetter`
  - `conflictInterest`

## TC-11 HR Manages Any Candidate Form

Role: HR

Steps:

1. Login as HR.
2. Send `GET` to `/candidates/<any_candidate_id>/employee-form`.
3. Send `POST` or `PUT` to the same route with updates in multiple sections.
4. Fetch the form again.

Expected result:

- HR can read any candidate form.
- HR can update all form sections.
- Response includes all employee form sections.

## TC-12 Recruiter Manages Assigned Candidate Form

Role: Recruiter

Steps:

1. Login as Recruiter.
2. Use a candidate where `officer_user_id` is the recruiter.
3. Send `GET` to `/candidates/<assigned_candidate_id>/employee-form`.
4. Send `POST` or `PUT` with updates.
5. Fetch the form again.

Expected result:

- Recruiter can read assigned candidate form.
- Recruiter can update assigned candidate form.
- Response includes all employee form sections.

## TC-13 Recruiter Cannot Manage Unassigned Candidate Form

Role: Recruiter

Steps:

1. Login as Recruiter.
2. Use a candidate not assigned to the recruiter.
3. Send `GET`, `POST`, or `PUT` to `/candidates/<unassigned_candidate_id>/employee-form`.

Expected result:

- Access is denied.
- Response status is `404`.
- Candidate data is not changed.

## TC-14 Candidate Submits Employee Form

Role: Candidate

Steps:

1. Login as candidate.
2. Send `POST` to `/candidates/<own_candidate_id>/employee-form/submit`.
3. Fetch the employee form again.

Expected result:

- Submit succeeds.
- `candidateStage` becomes `submitted`.
- Previous form review note and reviewer metadata are cleared.

## TC-15 HR Approves Submitted Candidate Form

Role: HR

Steps:

1. Login as HR.
2. Use a candidate form where `candidateStage` is `submitted`.
3. Send `POST` to `/candidates/<candidate_id>/employee-form/approve`.
4. Optionally include a review note:

```json
{
  "review_note": "Approved by HR"
}
```

Expected result:

- Approval succeeds.
- `candidateStage` becomes `accepted`.
- Review note, reviewer, and review date are stored.

## TC-16 HR Rejects Submitted Candidate Form

Role: HR

Steps:

1. Login as HR.
2. Use a candidate form where `candidateStage` is `submitted`.
3. Send `POST` to `/candidates/<candidate_id>/employee-form/reject`.
4. Include a rejection note:

```json
{
  "reviewNote": "Missing declaration signature"
}
```

Expected result:

- Rejection succeeds.
- `candidateStage` becomes `rejected`.
- Review note, reviewer, and review date are stored.

## TC-17 Candidate Cannot Approve Or Reject Form

Role: Candidate

Steps:

1. Login as candidate.
2. Send `POST` to `/candidates/<own_candidate_id>/employee-form/approve`.
3. Send `POST` to `/candidates/<own_candidate_id>/employee-form/reject`.

Expected result:

- Both requests are denied.
- Response status is `403`.
- Candidate form status is not changed by these requests.

## TC-18 HR Cannot Approve Draft Candidate Form

Role: HR

Steps:

1. Login as HR.
2. Use a candidate form where `candidateStage` is `draft`.
3. Send `POST` to `/candidates/<candidate_id>/employee-form/approve`.

Expected result:

- Request fails.
- Response status is `400`.
- Error says only submitted candidate forms can be approved or rejected.

## TC-19 Candidate Lists Own Documents

Role: Candidate

Steps:

1. Login as candidate.
2. Send `GET` to `/candidate/documents`.

Expected result:

- Candidate sees only their own documents.
- Response includes grouped documents.
- Response includes required, submitted, and accepted counts.

## TC-20 Candidate Uploads Own Document

Role: Candidate

Steps:

1. Login as candidate.
2. Pick one own document line.
3. Send multipart `POST` to `/candidate/documents/<document_id>/upload` with field `file`.
4. Fetch documents again.

Expected result:

- Upload succeeds.
- Document status becomes `submitted`.
- Document has attachment metadata.
- Submitted count increases.

## TC-21 Candidate Cannot Access Other Candidate Document

Role: Candidate

Steps:

1. Login as candidate A.
2. Use a document id belonging to candidate B.
3. Send `GET` to `/candidate/documents/<document_id>/content`.

Expected result:

- Access is denied.
- Response status is `404`.

## TC-22 General Staff Has Own Document CRUD

Role: Candidate (General staff)

Steps:

1. Login as Candidate (General staff).
2. Upload one own document.
3. Fetch document content.
4. Delete/reset the uploaded document with `DELETE /candidate/documents/<document_id>`.
5. Fetch documents again.

Expected result:

- Upload succeeds.
- Content can be viewed.
- Delete/reset succeeds.
- Document status returns to `missing`.
- Attachment is removed.

## TC-23 Finance Staff Has Own Document CRUD

Role: Candidate (Finance staff)

Steps:

1. Login as Candidate (Finance staff).
2. Upload one own document.
3. Fetch document content.
4. Delete/reset the uploaded document with `DELETE /candidate/documents/<document_id>`.
5. Fetch documents again.

Expected result:

- Upload succeeds.
- Content can be viewed.
- Delete/reset succeeds.
- Document status returns to `missing`.
- Attachment is removed.

## TC-24 Recruiter Lists Assigned Candidate Documents

Role: Recruiter

Steps:

1. Login as Recruiter.
2. Send `GET` to `/candidate/documents?candidate_id=<assigned_candidate_id>`.
3. Send `GET` to `/candidates/documents`.

Expected result:

- Recruiter sees assigned candidate documents.
- Recruiter does not see unassigned candidate documents.

## TC-25 Recruiter Uploads Assigned Candidate Document

Role: Recruiter

Steps:

1. Login as Recruiter.
2. Pick a document belonging to an assigned candidate.
3. Send multipart `POST` to `/candidate/documents/<document_id>/upload` with field `file`.
4. Fetch the document list.

Expected result:

- Upload succeeds.
- Document status becomes `submitted`.
- Attachment metadata is present.

## TC-26 Recruiter Cannot Upload Unassigned Candidate Document

Role: Recruiter

Steps:

1. Login as Recruiter.
2. Pick a document belonging to an unassigned candidate.
3. Send multipart `POST` to `/candidate/documents/<document_id>/upload` with field `file`.

Expected result:

- Access is denied.
- Response status is `404`.
- Document is not changed.

## TC-27 Recruiter Reviews Assigned Candidate Document

Role: Recruiter

Steps:

1. Login as Recruiter.
2. Upload or select an already submitted document for an assigned candidate.
3. Send `POST` to `/candidate/documents/<document_id>/accept`.
4. Repeat with another submitted document and send `POST` to `/candidate/documents/<document_id>/reject` with `review_note`.

Expected result:

- Accept succeeds for assigned candidate document.
- Reject succeeds for assigned candidate document.
- `reviewed_by`, `reviewed_on`, and `review_note` are updated.

## TC-28 HR Lists All Candidate Documents

Role: HR

Steps:

1. Login as HR.
2. Send `GET` to `/candidates/documents`.

Expected result:

- HR sees all candidate document groups.
- Response count includes all visible candidates.

## TC-29 HR Uploads Any Candidate Document

Role: HR

Steps:

1. Login as HR.
2. Pick any candidate document.
3. Send multipart `POST` to `/candidate/documents/<document_id>/upload` with field `file`.

Expected result:

- Upload succeeds.
- Document status becomes `submitted`.
- Attachment metadata is present.

## TC-30 HR Reviews Any Candidate Document

Role: HR

Steps:

1. Login as HR.
2. Upload or select any submitted candidate document.
3. Send `POST` to `/candidate/documents/<document_id>/review` with:

```json
{
  "status": "accepted",
  "review_note": "Approved"
}
```

Expected result:

- Review succeeds.
- Document status becomes `accepted`.
- Review metadata is stored.

## TC-31 Review Requires Uploaded File

Role: HR or Recruiter

Steps:

1. Login as HR or Recruiter.
2. Pick a document with no attachment.
3. Send `POST` to `/candidate/documents/<document_id>/accept`.

Expected result:

- Review fails.
- Response status is `400`.
- Error explains that a document without uploaded file cannot be reviewed.

## TC-32 Invalid Review Status Is Rejected

Role: HR or Recruiter

Steps:

1. Login as HR or Recruiter.
2. Pick a submitted document the user can review.
3. Send `POST` to `/candidate/documents/<document_id>/review` with:

```json
{
  "status": "pending"
}
```

Expected result:

- Request fails.
- Response status is `400`.
- Error says status must be `accepted` or `rejected`.
