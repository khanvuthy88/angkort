# -*- coding: utf-8 -*-

import base64
import json

from odoo.tests.common import HttpCase, new_test_user, tagged


PNG_1X1 = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BCQAHBQICJmhD1AAAAABJRU5ErkJggg=="
)


@tagged("-at_install", "post_install")
class TestCandidateApi(HttpCase):
    readonly_enabled = False
    CANDIDATE_PASSWORD = "Pl1bhD@2!candidate"
    OTHER_PASSWORD = "Pl1bhD@2!othercandidate"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("auth_password_policy.minlength", 4)

        cls.candidate_user = new_test_user(
            cls.env,
            login="candidate.portal@example.com",
            password=cls.CANDIDATE_PASSWORD,
            groups="base.group_portal,angkot_candidate.group_candidate_portal",
            name="Candidate Portal",
        )
        cls.other_user = new_test_user(
            cls.env,
            login="other.portal@example.com",
            password=cls.OTHER_PASSWORD,
            groups="base.group_portal,angkot_candidate.group_candidate_portal",
            name="Other Portal",
        )

        cls.candidate = cls.env["hr.candidate"].sudo().create({
            "partner_name": "Primary Candidate",
            "portal_user_id": cls.candidate_user.id,
            "email_from": "candidate.portal@example.com",
            "partner_phone": "010101010",
        })
        cls.other_candidate = cls.env["hr.candidate"].sudo().create({
            "partner_name": "Other Candidate",
            "portal_user_id": cls.other_user.id,
            "email_from": "other.portal@example.com",
            "partner_phone": "020202020",
        })

    def _json_headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post_json(self, path, payload):
        return self.url_open(path, data=json.dumps(payload), headers=self._json_headers())

    def _authenticate_candidate(self):
        self.authenticate(self.candidate_user.login, self.CANDIDATE_PASSWORD)

    def _authenticate_other_candidate(self):
        self.authenticate(self.other_user.login, self.OTHER_PASSWORD)

    def test_get_employee_form_returns_sectioned_payload(self):
        self._authenticate_candidate()

        response = self.url_open("/angkort/api/v1/candidate/employee-form")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["status"], payload)
        self.assertEqual(payload["data"]["candidateId"], self.candidate.id)
        self.assertIn("personalInformation", payload["data"])
        self.assertIn("familyInformation", payload["data"])
        self.assertEqual(payload["data"]["personalInformation"]["englishName"], "Primary Candidate")

    def test_post_employee_form_updates_nested_sections(self):
        self._authenticate_candidate()

        response = self._post_json("/angkort/api/v1/candidate/employee-form", {
            "personalInformation": {
                "englishName": "John Doe",
                "khmerName": "ជន ដូ",
                "position": "Operator",
                "gender": "male",
                "maritalStatus": "single",
                "placeOfBirth": "Kampong Cham",
                "currentAddress": "Current Address",
                "permanentAddress": "Permanent Address",
                "nationalIdOrPassport": "A1234567",
                "contactNumber": "012345678",
                "dateOfBirth": "1999-12-31",
            },
            "familyInformation": {
                "fatherName": "Father Test",
                "fatherJob": "Farmer",
                "motherName": "Mother Test",
                "motherJob": "Vendor",
                "numberOfSiblings": "4",
                "contactNumber": "099999999",
                "currentAddress": "Family Current",
                "permanentAddress": "Family Permanent",
            },
            "spouseInformation": {
                "name": "Spouse Test",
                "job": "Teacher",
                "numberOfChildren": "2",
                "contactNumber": "088888888",
                "currentAddress": "Spouse Current",
                "permanentAddress": "Spouse Permanent",
            },
            "educationInformation": {
                "degreeTypes": "Bachelor",
                "major": "Accounting",
                "other": "Honors",
                "yearsOfStudy": "2018-2022",
            },
            "shortCourseInformation": {
                "shortCourseCertificates": "Computer Skills",
                "shortCourseDuration": "6 months",
                "major": "Excel",
                "other": "Advanced",
            },
            "employmentHistory": {
                "name": "Latest Co",
                "position": "Clerk",
                "durationOfWork": "2 years",
                "jobResponsibility": "Handle records",
                "other": "Night shift",
            },
            "otherInformation": {
                "hadInjury": True,
                "hadInjuryDescription": "Recovered leg injury",
                "arrested": False,
                "arrestedDescription": "",
            },
            "declaration": {
                "date": "2026-04-05",
                "signature": "<svg>signature</svg>",
            },
        })

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["status"], payload)

        self.candidate.invalidate_recordset([
            "english_name", "khmer_name", "position_name", "gender", "marital_status",
            "date_of_birth", "father_name", "number_of_siblings", "spouse_name",
            "degree_types", "short_course_major", "latest_institution_name",
            "had_injury", "declaration_signature",
        ])
        self.assertEqual(self.candidate.english_name, "John Doe")
        self.assertEqual(self.candidate.khmer_name, "ជន ដូ")
        self.assertEqual(self.candidate.position_name, "Operator")
        self.assertEqual(self.candidate.gender, "male")
        self.assertEqual(str(self.candidate.date_of_birth), "1999-12-31")
        self.assertEqual(self.candidate.father_name, "Father Test")
        self.assertEqual(self.candidate.number_of_siblings, 4)
        self.assertEqual(self.candidate.spouse_name, "Spouse Test")
        self.assertEqual(self.candidate.degree_types, "Bachelor")
        self.assertEqual(self.candidate.short_course_major, "Excel")
        self.assertEqual(self.candidate.latest_institution_name, "Latest Co")
        self.assertTrue(self.candidate.had_injury)
        self.assertEqual(self.candidate.declaration_signature, "<svg>signature</svg>")

    def test_post_employee_form_accepts_photo_upload_and_photo_endpoint(self):
        self._authenticate_candidate()

        response = self.url_open(
            "/angkort/api/v1/candidate/employee-form",
            data={"englishName": "Photo Candidate"},
            files={"photo": ("photo.png", PNG_1X1, "image/png")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.candidate.invalidate_recordset(["image_1920", "english_name"])
        self.assertTrue(self.candidate.image_1920)
        self.assertEqual(self.candidate.english_name, "Photo Candidate")

        photo_response = self.url_open("/angkort/api/v1/candidate/employee-form/photo")
        self.assertEqual(photo_response.status_code, 200, photo_response.text)
        self.assertEqual(photo_response.headers.get("Content-Type"), "image/png")
        self.assertTrue(photo_response.content)

    def test_candidate_can_list_and_upload_own_document(self):
        self._authenticate_candidate()
        document = self.candidate.document_ids[:1]
        self.assertTrue(document)

        list_response = self.url_open("/angkort/api/v1/candidate/documents")
        self.assertEqual(list_response.status_code, 200, list_response.text)
        list_payload = list_response.json()
        self.assertTrue(list_payload["status"], list_payload)
        self.assertGreaterEqual(len(list_payload["data"]["documents"]), 1)

        upload_response = self.url_open(
            f"/angkort/api/v1/candidate/documents/{document.id}/upload",
            files={"file": ("passport.pdf", b"%PDF-1.4 test pdf", "application/pdf")},
        )
        self.assertEqual(upload_response.status_code, 201, upload_response.text)
        upload_payload = upload_response.json()
        self.assertTrue(upload_payload["status"], upload_payload)

        document.invalidate_recordset(["status", "attachment_id", "filename"])
        self.assertEqual(document.status, "submitted")
        self.assertTrue(document.attachment_id)
        self.assertEqual(document.filename, "passport.pdf")

    def test_candidate_cannot_access_other_candidates_document(self):
        target_document = self.candidate.document_ids[:1]
        self.assertTrue(target_document)
        target_document.portal_upload_file(
            type("Upload", (), {
                "filename": "nid.pdf",
                "content_type": "application/pdf",
                "read": staticmethod(lambda: b"%PDF-1.4 test pdf"),
            })(),
            self.candidate_user,
        )

        self._authenticate_other_candidate()
        response = self.url_open(f"/angkort/api/v1/candidate/documents/{target_document.id}/content")

        self.assertEqual(response.status_code, 404, response.text)
        payload = response.json()
        self.assertFalse(payload["status"])
