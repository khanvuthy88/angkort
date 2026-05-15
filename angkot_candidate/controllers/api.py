# -*- coding: utf-8 -*-

import base64
import datetime
import hashlib
import json
import jwt

from odoo import fields, http
from odoo.http import content_disposition, request


BASE_URL = "/angkort/api/v1"


class CandidateDocumentApi(http.Controller):

    EMPLOYEE_FORM_FIELD_MAP = {
        "position": ("position_name", "char"),
        "khmerName": ("khmer_name", "char"),
        "englishName": ("english_name", "char"),
        "gender": ("gender", "char"),
        "maritalStatus": ("marital_status", "char"),
        "placeOfBirth": ("place_of_birth", "text"),
        "currentAddress": ("current_address", "text"),
        "permanentAddress": ("permanent_address", "text"),
        "nationalIdOrPassport": ("national_id_or_passport", "char"),
        "contactNumber": ("partner_phone", "char"),
        "dateOfBirth": ("date_of_birth", "date"),
        "fatherJob": ("father_job", "char"),
        "fatherName": ("father_name", "char"),
        "motherJob": ("mother_job", "char"),
        "motherName": ("mother_name", "char"),
        "numberOfSiblings": ("number_of_siblings", "int"),
        "familyContactNumber": ("family_contact_number", "char"),
        "familyCurrentAddress": ("family_current_address", "text"),
        "familyPermanentAddress": ("family_permanent_address", "text"),
        "job": ("spouse_job", "char"),
        "name": ("spouse_name", "char"),
        "numberOfChildren": ("number_of_children", "int"),
        "spouseContactNumber": ("spouse_contact_number", "char"),
        "spouseCurrentAddress": ("spouse_current_address", "text"),
        "spousePermanentAddress": ("spouse_permanent_address", "text"),
        "degreeTypes": ("degree_types", "char"),
        "major": ("education_major", "char"),
        "other": ("education_notes", "text"),
        "yearsOfStudy": ("years_of_study", "char"),
        "shortCourseCertificates": ("short_course_certificates", "char"),
        "shortCourseDuration": ("short_course_duration", "char"),
        "shortCourseMajor": ("short_course_major", "char"),
        "shortCourseOther": ("short_course_notes", "text"),
        "durationOfWork": ("duration_of_work", "char"),
        "jobResponsibility": ("job_responsibility", "text"),
        "latestInstitutionName": ("latest_institution_name", "char"),
        "employmentHistoryPosition": ("employment_history_position", "char"),
        "employmentHistoryOther": ("employment_history_notes", "text"),
        "hadInjury": ("had_injury", "bool"),
        "hadInjuryDescription": ("had_injury_description", "text"),
        "arrested": ("arrested", "bool"),
        "arrestedDescription": ("arrested_description", "text"),
        "date": ("declaration_date", "date"),
        "signature": ("declaration_signature", "text"),
    }

    @http.route(f"{BASE_URL}/candidate/documents/<path:subpath>", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    @http.route(f"{BASE_URL}/candidate/documents", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    @http.route(f"{BASE_URL}/candidates/documents", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    def candidate_documents_options(self, subpath=None, **kwargs):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
            "Access-Control-Max-Age": "86400",
        }
        return request.make_response("", headers=headers)

    def error_response(self, message, status=400, errors=None):
        payload = {
            "status": "error",
            "message": message,
            "statusCode": status
        }
        if errors:
            payload["errors"] = errors
        return request.make_json_response(payload, status=status)

    def success_response(self, message=None, data=None, meta=None, status=200):
        payload = {
            "status": "success",
            "message": message
        }
        if data is not None:
            payload["data"] = data
        if meta:
            payload["meta"] = meta
        return request.make_json_response(payload, status=status)

    def _get_secret_key(self):
        return request.env["ir.config_parameter"].sudo().get_param("database.secret")

    def _issue_tokens(self, user_id, secret_key):
        now = datetime.datetime.utcnow()
        access_payload = {
            "user_id": user_id,
            "token_type": "access",
            "iat": now,
            "exp": now + datetime.timedelta(hours=1),
        }
        refresh_payload = {
            "user_id": user_id,
            "token_type": "refresh",
            "iat": now,
            "exp": now + datetime.timedelta(days=30),
        }
        access_token = jwt.encode(access_payload, secret_key, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, secret_key, algorithm="HS256")
        return access_token, refresh_token

    def _store_token_record(self, user_id, access_token, refresh_token, secret_key):
        """Store tokens in res.user.token if e_menu is installed; silently skip otherwise."""
        if not request.env.registry.get("res.user.token"):
            return
        try:
            now = datetime.datetime.utcnow()
            access_payload = jwt.decode(access_token, secret_key, algorithms=["HS256"])
            refresh_payload = jwt.decode(refresh_token, secret_key, algorithms=["HS256"])
            request.env["res.user.token"].sudo().search([
                ("user_id", "=", user_id), ("active", "=", True)
            ]).write({"active": False})
            request.env["res.user.token"].sudo().create({
                "user_id": user_id,
                "access_token": hashlib.sha256(access_token.encode()).hexdigest(),
                "refresh_token": hashlib.sha256(refresh_token.encode()).hexdigest(),
                "active": True,
                "expires_at": datetime.datetime.utcfromtimestamp(access_payload["exp"]),
            })
        except Exception:
            pass

    def _get_user_role_enum(self, user):
        if not user or not user.exists():
            return "user"
        if user.has_group("angkot_candidate.group_candidate_hr_reviewer"):
            return "hr_document_reviewer"
        if user.has_group("angkot_candidate.group_candidate_encharge_officer"):
            return "encharge_officer"
        if user.has_group("angkot_candidate.group_candidate_portal"):
            return "candidate"
        return "user"

    def _get_bearer_user(self):
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return request.env["res.users"]

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return request.env["res.users"]

        secret_key = self._get_secret_key()
        if not secret_key:
            return request.env["res.users"]

        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return request.env["res.users"]

        if payload.get("token_type") != "access":
            return request.env["res.users"]

        user_id = payload.get("user_id")
        # If e_menu is installed, enforce DB-side revocation check.
        if request.env.registry.get("res.user.token"):
            hashed_token = hashlib.sha256(token.encode()).hexdigest()
            token_record = request.env["res.user.token"].sudo().search([
                ("access_token", "=", hashed_token),
                ("active", "=", True),
            ], limit=1)
            if not token_record:
                return request.env["res.users"]
            if token_record.expires_at and token_record.expires_at <= fields.Datetime.now():
                return request.env["res.users"]
            if token_record.user_id.id != user_id:
                return request.env["res.users"]

        user = request.env["res.users"].sudo().browse(user_id)
        return user if user.exists() else request.env["res.users"]

    @http.route(f"{BASE_URL}/login", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    def candidate_login_options(self, **kwargs):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
            "Access-Control-Max-Age": "86400",
        }
        return request.make_response("", headers=headers)

    @http.route(f"{BASE_URL}/login", auth="none", type="http", methods=["POST"], csrf=False, cors="*")
    def candidate_login(self, **kwargs):
        payload = self._parse_request_payload()
        username = payload.get("username") or payload.get("login") or ""
        password = payload.get("password") or ""

        if not username or not password:
            return self.error_response("Missing credentials", errors=["'username' and 'password' are required"], status=400)

        secret_key = self._get_secret_key()
        if not secret_key:
            return self.error_response("Server misconfiguration", errors=["JWT secret key is not configured"], status=500)

        credential = {"type": "password", "login": username, "password": password}
        try:
            auth_info = request.session.authenticate(request.env.cr.dbname, credential)
            uid = auth_info.get("uid") if isinstance(auth_info, dict) else request.session.uid
        except Exception:
            uid = False

        if not uid:
            return self.error_response("Authentication failed", errors=["Invalid username or password"], status=401)

        user = request.env["res.users"].sudo().browse(uid)
        access_token, refresh_token = self._issue_tokens(uid, secret_key)
        self._store_token_record(uid, access_token, refresh_token, secret_key)

        return self.success_response("Login successful", data={
            "user_id": uid,
            "name": user.name,
            "email": user.email or username,
            "role": self._get_user_role_enum(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        })

    @http.route(f"{BASE_URL}/refresh", auth="none", type="http", methods=["POST"], csrf=False, cors="*")
    def candidate_refresh(self, **kwargs):
        payload = self._parse_request_payload()
        refresh_token = payload.get("refresh_token") or ""

        if not refresh_token:
            return self.error_response("Missing token", errors=["'refresh_token' is required"], status=400)

        secret_key = self._get_secret_key()
        if not secret_key:
            return self.error_response("Server misconfiguration", errors=["JWT secret key is not configured"], status=500)

        try:
            token_payload = jwt.decode(refresh_token, secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return self.error_response("Token expired", errors=["Refresh token has expired"], status=401)
        except jwt.InvalidTokenError:
            return self.error_response("Invalid token", errors=["Refresh token is invalid"], status=401)

        if token_payload.get("token_type") != "refresh":
            return self.error_response("Invalid token type", errors=["Provided token is not a refresh token"], status=401)

        user_id = token_payload.get("user_id")
        user = request.env["res.users"].sudo().browse(user_id)
        if not user.exists():
            return self.error_response("User not found", errors=["Associated user no longer exists"], status=401)

        new_access_token, new_refresh_token = self._issue_tokens(user_id, secret_key)
        self._store_token_record(user_id, new_access_token, new_refresh_token, secret_key)

        return self.success_response("Token refreshed", data={
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        })

    def _get_authenticated_user(self):
        user = request.env.user
        if user and not user._is_public():
            return user
        bearer_user = self._get_bearer_user()
        if bearer_user and bearer_user.exists():
            request.update_env(user=bearer_user.id)
            return request.env.user
        return request.env["res.users"]

    def _get_candidate_for_user(self, user):
        if not user or not user.exists():
            return request.env["hr.candidate"]
        return request.env["hr.candidate"].sudo().search([
            ("portal_user_id", "=", user.id),
        ], limit=1)

    def _get_document_candidate_for_user(self, user, candidate_id=None):
        if not user or not user.exists():
            return request.env["hr.candidate"]

        domain = []
        if candidate_id:
            domain.append(("id", "=", candidate_id))

        if user.has_group("angkot_candidate.group_candidate_hr_reviewer"):
            return request.env["hr.candidate"].sudo().search(domain, limit=1)

        if user.has_group("angkot_candidate.group_candidate_encharge_officer"):
            domain.append(("officer_user_id", "=", user.id))
            return request.env["hr.candidate"].sudo().search(domain, limit=1)

        domain.append(("portal_user_id", "=", user.id))
        return request.env["hr.candidate"].sudo().search(domain, limit=1)

    def _get_candidate_basic_for_user(self, user, candidate_id):
        if not user or not user.exists():
            return request.env["hr.candidate"]

        domain = [("id", "=", candidate_id)]
        if user.has_group("angkot_candidate.group_candidate_hr_reviewer"):
            return request.env["hr.candidate"].sudo().search(domain, limit=1)

        if user.has_group("angkot_candidate.group_candidate_encharge_officer"):
            domain.append(("officer_user_id", "=", user.id))
            return request.env["hr.candidate"].sudo().search(domain, limit=1)

        domain.append(("portal_user_id", "=", user.id))
        return request.env["hr.candidate"].sudo().search(domain, limit=1)

    def _get_document_candidates_for_user(self, user):
        if not user or not user.exists():
            return request.env["hr.candidate"]
        if user.has_group("angkot_candidate.group_candidate_hr_reviewer"):
            return request.env["hr.candidate"].sudo().search([], order="id")
        if user.has_group("angkot_candidate.group_candidate_encharge_officer"):
            return request.env["hr.candidate"].sudo().search([
                ("officer_user_id", "=", user.id),
            ], order="id")
        return request.env["hr.candidate"].sudo().search([
            ("portal_user_id", "=", user.id),
        ], order="id")

    def _get_candidates_for_user(self, user):
        return self._get_document_candidates_for_user(user)

    def _can_access_candidate_document(self, user, document):
        if not user or not user.exists() or not document:
            return False
        if user.has_group("angkot_candidate.group_candidate_hr_reviewer"):
            return True
        if user.has_group("angkot_candidate.group_candidate_encharge_officer"):
            return document.officer_user_id.id == user.id
        return document.portal_user_id.id == user.id

    def _can_review_candidate_document(self, user, document):
        if not user or not user.exists() or not document:
            return False
        if user.has_group("angkot_candidate.group_candidate_hr_reviewer"):
            return True
        if user.has_group("angkot_candidate.group_candidate_encharge_officer"):
            return document.officer_user_id.id == user.id
        return False

    def _parse_request_payload(self):
        if request.httprequest.data:
            try:
                return json.loads(request.httprequest.data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        return dict(request.params)

    def _coerce_form_value(self, value, value_type):
        if value_type in ("char", "text"):
            return value or False
        if value_type == "date":
            return value or False
        if value_type == "int":
            if value in (None, "", False):
                return False
            return int(value)
        if value_type == "bool":
            if isinstance(value, bool):
                return value
            if value in (None, "", False):
                return False
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on")
            return bool(value)
        return value

    def _extract_employee_form_vals(self, payload):
        vals = {}
        if not isinstance(payload, dict):
            return vals

        personal = payload.get("personalInformation") or {}
        family = payload.get("familyInformation") or {}
        spouse = payload.get("spouseInformation") or {}
        education = payload.get("educationInformation") or {}
        short_course = payload.get("shortCourseInformation") or {}
        employment = payload.get("employmentHistory") or {}
        other = payload.get("otherInformation") or {}
        declaration = payload.get("declaration") or {}

        for source in (personal, payload):
            if not isinstance(source, dict):
                continue
            for api_key, (field_name, value_type) in self.EMPLOYEE_FORM_FIELD_MAP.items():
                if api_key in source:
                    vals[field_name] = self._coerce_form_value(source.get(api_key), value_type)

        nested_mappings = (
            (family, {
                "fatherName": ("father_name", "char"),
                "fatherJob": ("father_job", "char"),
                "motherName": ("mother_name", "char"),
                "motherJob": ("mother_job", "char"),
                "numberOfSiblings": ("number_of_siblings", "int"),
                "contactNumber": ("family_contact_number", "char"),
                "currentAddress": ("family_current_address", "text"),
                "permanentAddress": ("family_permanent_address", "text"),
            }),
            (spouse, {
                "name": ("spouse_name", "char"),
                "job": ("spouse_job", "char"),
                "numberOfChildren": ("number_of_children", "int"),
                "contactNumber": ("spouse_contact_number", "char"),
                "currentAddress": ("spouse_current_address", "text"),
                "permanentAddress": ("spouse_permanent_address", "text"),
            }),
            (education, {
                "degreeTypes": ("degree_types", "char"),
                "major": ("education_major", "char"),
                "other": ("education_notes", "text"),
                "yearsOfStudy": ("years_of_study", "char"),
            }),
            (short_course, {
                "shortCourseCertificates": ("short_course_certificates", "char"),
                "shortCourseDuration": ("short_course_duration", "char"),
                "major": ("short_course_major", "char"),
                "other": ("short_course_notes", "text"),
            }),
            (employment, {
                "name": ("latest_institution_name", "char"),
                "position": ("employment_history_position", "char"),
                "durationOfWork": ("duration_of_work", "char"),
                "jobResponsibility": ("job_responsibility", "text"),
                "other": ("employment_history_notes", "text"),
            }),
            (other, {
                "hadInjury": ("had_injury", "bool"),
                "hadInjuryDescription": ("had_injury_description", "text"),
                "arrested": ("arrested", "bool"),
                "arrestedDescription": ("arrested_description", "text"),
            }),
            (declaration, {
                "date": ("declaration_date", "date"),
                "signature": ("declaration_signature", "text"),
            }),
        )
        for source, mapping in nested_mappings:
            if not isinstance(source, dict):
                continue
            for api_key, (field_name, value_type) in mapping.items():
                if api_key in source:
                    vals[field_name] = self._coerce_form_value(source.get(api_key), value_type)
        return vals

    def _stringify_int(self, value):
        return "" if value in (False, None) else str(value)

    def _serialize_employee_form(self, candidate):
        return {
            "candidateId": candidate.id,
            "candidateName": candidate.display_name,
            "personalInformation": {
                "photoUrl": (request.httprequest.url_root.rstrip('/') + BASE_URL + "/candidate/employee-form/photo") if candidate.image_1920 else "",
                "position": candidate.position_name or "",
                "khmerName": candidate.khmer_name or "",
                "englishName": candidate.english_name or candidate.partner_name or "",
                "gender": candidate.gender or "",
                "maritalStatus": candidate.marital_status or "",
                "placeOfBirth": candidate.place_of_birth or "",
                "currentAddress": candidate.current_address or "",
                "permanentAddress": candidate.permanent_address or "",
                "nationalIdOrPassport": candidate.national_id_or_passport or "",
                "contactNumber": candidate.partner_phone or "",
                "dateOfBirth": candidate.date_of_birth.isoformat() if candidate.date_of_birth else None,
            },
            "familyInformation": {
                "fatherJob": candidate.father_job or "",
                "fatherName": candidate.father_name or "",
                "motherJob": candidate.mother_job or "",
                "motherName": candidate.mother_name or "",
                "numberOfSiblings": self._stringify_int(candidate.number_of_siblings),
                "contactNumber": candidate.family_contact_number or "",
                "currentAddress": candidate.family_current_address or "",
                "permanentAddress": candidate.family_permanent_address or "",
            },
            "spouseInformation": {
                "name": candidate.spouse_name or "",
                "job": candidate.spouse_job or "",
                "numberOfChildren": self._stringify_int(candidate.number_of_children),
                "contactNumber": candidate.spouse_contact_number or "",
                "currentAddress": candidate.spouse_current_address or "",
                "permanentAddress": candidate.spouse_permanent_address or "",
            },
            "educationInformation": {
                "degreeTypes": candidate.degree_types or "",
                "major": candidate.education_major or "",
                "other": candidate.education_notes or "",
                "yearsOfStudy": candidate.years_of_study or "",
            },
            "shortCourseInformation": {
                "shortCourseCertificates": candidate.short_course_certificates or "",
                "shortCourseDuration": candidate.short_course_duration or "",
                "major": candidate.short_course_major or "",
                "other": candidate.short_course_notes or "",
            },
            "employmentHistory": {
                "name": candidate.latest_institution_name or "",
                "position": candidate.employment_history_position or "",
                "durationOfWork": candidate.duration_of_work or "",
                "jobResponsibility": candidate.job_responsibility or "",
                "other": candidate.employment_history_notes or "",
            },
            "otherInformation": {
                "hadInjury": bool(candidate.had_injury),
                "hadInjuryDescription": candidate.had_injury_description or "",
                "arrested": bool(candidate.arrested),
                "arrestedDescription": candidate.arrested_description or "",
            },
            "declaration": {
                "date": candidate.declaration_date.isoformat() if candidate.declaration_date else None,
                "signature": candidate.declaration_signature or "",
            },
        }

    def _serialize_candidate_basic(self, candidate):
        base_url = request.httprequest.url_root.rstrip("/")
        return {
            "id": candidate.id,
            "name": candidate.display_name,
            "photoUrl": (
                f"{base_url}{BASE_URL}/candidates/{candidate.id}/photo"
                if candidate.image_1920 else ""
            ),
            "khmerName": candidate.khmer_name or "",
            "englishName": candidate.english_name or candidate.partner_name or "",
            "position": candidate.position_name or "",
            "gender": candidate.gender or "",
            "maritalStatus": candidate.marital_status or "",
            "dateOfBirth": candidate.date_of_birth.isoformat() if candidate.date_of_birth else None,
            "contactNumber": candidate.partner_phone or "",
            "email": candidate.email_from or "",
            "nationalIdOrPassport": candidate.national_id_or_passport or "",
            "officer": {
                "id": candidate.officer_user_id.id or False,
                "name": candidate.officer_user_id.name or "",
            },
            "documentSummary": {
                "required": candidate.required_document_count,
                "submitted": candidate.submitted_document_count,
                "accepted": candidate.accepted_document_count,
            },
        }

    def _serialize_document(self, document):
        attachment = document.attachment_id
        return {
            "id": document.id,
            "name": document.document_type_id.name,
            "code": document.document_type_id.code,
            "category": document.category,
            "required": bool(document.required),
            "status": document.status,
            "filename": document.filename or "",
            "mimetype": document.mimetype or "",
            "upload_date": document.upload_date.isoformat() if document.upload_date else None,
            "review_note": document.review_note or "",
            "reviewed_by": document.reviewed_by.name if document.reviewed_by else "",
            "reviewed_on": document.reviewed_on.isoformat() if document.reviewed_on else None,
            "has_attachment": bool(attachment),
            "view_url": (request.httprequest.url_root.rstrip('/') + "/angkort/api/v1/candidate/documents/%s/content" % document.id) if attachment else "",
        }

    def _serialize_document_groups(self, documents):
        selection = dict(request.env["angkot.candidate.document.type"]._fields["category"].selection)
        groups = []
        for category, label in selection.items():
            category_documents = documents.filtered(lambda document: document.category == category)
            if not category_documents:
                continue
            required_documents = category_documents.filtered(lambda document: document.required)
            completed_documents = required_documents.filtered(lambda document: document.status in ("submitted", "accepted"))
            groups.append({
                "category": category,
                "label": label,
                "completed": len(completed_documents),
                "total": len(required_documents),
                "documents": [self._serialize_document(document) for document in category_documents],
            })
        return groups

    def _serialize_candidate_documents(self, candidate):
        documents = candidate.document_ids.sorted(key=lambda doc: (doc.document_type_sequence, doc.id))
        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.display_name,
            "required_document_count": candidate.required_document_count,
            "submitted_document_count": candidate.submitted_document_count,
            "accepted_document_count": candidate.accepted_document_count,
            "document_groups": self._serialize_document_groups(documents),
        }

    @http.route(f"{BASE_URL}/candidate/employee-form/<path:subpath>", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    @http.route(f"{BASE_URL}/candidate/employee-form", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    def candidate_employee_form_options(self, subpath=None, **kwargs):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
            "Access-Control-Max-Age": "86400",
        }
        return request.make_response("", headers=headers)

    @http.route(f"{BASE_URL}/candidate/employee-form", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidate_employee_form(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidate = self._get_candidate_for_user(user)
        if not candidate:
            return self.error_response("Candidate not found", errors=["No candidate is linked to this user"], status=404)

        return self.success_response(
            "Candidate employee form fetched successfully",
            data=self._serialize_employee_form(candidate.sudo()),
        )

    @http.route(f"{BASE_URL}/candidate/employee-form", auth="public", type="http", methods=["POST", "PUT"], csrf=False, cors="*")
    def upsert_candidate_employee_form(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidate = self._get_candidate_for_user(user)
        if not candidate:
            return self.error_response("Candidate not found", errors=["No candidate is linked to this user"], status=404)

        payload = self._parse_request_payload()
        try:
            vals = self._extract_employee_form_vals(payload)
        except (TypeError, ValueError) as error:
            return self.error_response("Invalid form payload", errors=[str(error)], status=400)

        photo_file = request.httprequest.files.get("photo")
        photo_base64 = payload.get("photoBase64") if isinstance(payload, dict) else None
        if photo_file and photo_file.filename:
            vals["image_1920"] = base64.b64encode(photo_file.read())
        elif photo_base64:
            vals["image_1920"] = photo_base64

        if not vals:
            return self.error_response("No form values were provided", errors=["Provide JSON fields or multipart form data"], status=400)

        try:
            candidate.sudo().write(vals)
        except Exception as error:
            return self.error_response("Unable to save employee form", errors=[str(error)], status=400)

        return self.success_response(
            "Candidate employee form saved successfully",
            data=self._serialize_employee_form(candidate.sudo()),
        )

    @http.route(f"{BASE_URL}/candidates", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidates(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidates = self._get_candidates_for_user(user)
        data = {
            "candidates": [self._serialize_candidate_basic(candidate) for candidate in candidates],
        }
        meta = {
            "count": len(candidates),
        }
        return self.success_response("Candidates fetched successfully", data=data, meta=meta)

    @http.route(f"{BASE_URL}/candidates/<int:candidate_id>", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidate(self, candidate_id, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidate = self._get_candidate_basic_for_user(user, candidate_id)
        if not candidate:
            return self.error_response("Candidate not found", errors=["The requested candidate is not available for this user"], status=404)

        return self.success_response(
            "Candidate fetched successfully",
            data=self._serialize_candidate_basic(candidate),
        )

    @http.route(f"{BASE_URL}/candidates/<int:candidate_id>/photo", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidate_photo(self, candidate_id, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidate = self._get_candidate_basic_for_user(user, candidate_id)
        if not candidate or not candidate.image_1920:
            return self.error_response("Photo not found", errors=["No candidate photo is available"], status=404)

        raw_content = base64.b64decode(candidate.image_1920)
        headers = [
            ("Content-Type", "image/png"),
            ("Content-Length", str(len(raw_content))),
            ("Content-Disposition", content_disposition("candidate-photo.png", disposition_type="inline")),
        ]
        return request.make_response(raw_content, headers)

    @http.route(f"{BASE_URL}/candidate/employee-form/photo", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidate_employee_form_photo(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidate = self._get_candidate_for_user(user)
        if not candidate or not candidate.image_1920:
            return self.error_response("Photo not found", errors=["No profile photo is available"], status=404)

        raw_content = base64.b64decode(candidate.image_1920)
        headers = [
            ("Content-Type", "image/png"),
            ("Content-Length", str(len(raw_content))),
            ("Content-Disposition", content_disposition("candidate-photo.png", disposition_type="inline")),
        ]
        return request.make_response(raw_content, headers)

    @http.route(f"{BASE_URL}/candidate/documents", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidate_documents(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidate_id = kwargs.get("candidate_id")
        try:
            candidate_id = int(candidate_id) if candidate_id else None
        except (TypeError, ValueError):
            return self.error_response("Invalid candidate", errors=["'candidate_id' must be an integer"], status=400)

        candidate = self._get_document_candidate_for_user(user, candidate_id=candidate_id)
        if not candidate:
            return self.error_response("Candidate not found", errors=["No candidate documents are available for this user"], status=404)

        candidate._ensure_required_document_lines()
        data = self._serialize_candidate_documents(candidate)
        return self.success_response("Candidate documents fetched successfully", data=data)

    @http.route(f"{BASE_URL}/candidates/documents", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidates_documents(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        candidates = self._get_document_candidates_for_user(user)
        candidates._ensure_required_document_lines()
        data = {
            "candidates": [self._serialize_candidate_documents(candidate) for candidate in candidates],
        }
        meta = {
            "count": len(candidates),
        }
        return self.success_response("Candidate documents fetched successfully", data=data, meta=meta)

    @http.route(
        f"{BASE_URL}/candidate/documents/<int:document_id>/upload",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def upload_candidate_document(self, document_id, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not document or document.portal_user_id.id != user.id:
            return self.error_response("Document not found", errors=["The requested document does not belong to the current candidate"], status=404)

        upload_file = request.httprequest.files.get("file")
        if not upload_file or not upload_file.filename:
            return self.error_response("Missing required file", errors=["Field 'file' is required"], status=400)

        try:
            document.portal_upload_file(upload_file, user)
        except Exception as error:
            return self.error_response("Upload failed", errors=[str(error)], status=400)

        return self.success_response(
            "Document uploaded successfully",
            data=self._serialize_document(document.sudo()),
            status=201,
        )

    def _review_candidate_document(self, document_id, status=None, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not document or not self._can_review_candidate_document(user, document):
            return self.error_response("Document not found", errors=["The requested document is not available for review"], status=404)

        payload = self._parse_request_payload()
        review_status = status or payload.get("status")
        review_note = payload.get("review_note")

        if review_status not in ("accepted", "rejected"):
            return self.error_response(
                "Invalid review status",
                errors=["'status' must be either 'accepted' or 'rejected'"],
                status=400,
            )

        if not document.attachment_id:
            return self.error_response(
                "Review failed",
                errors=["You cannot review a document that has no uploaded file"],
                status=400,
            )

        vals = {
            "status": review_status,
            "reviewed_by": user.id,
            "reviewed_on": fields.Datetime.now(),
        }
        if review_note is not None:
            vals["review_note"] = review_note or False

        try:
            document.sudo().write(vals)
        except Exception as error:
            return self.error_response("Review failed", errors=[str(error)], status=400)

        return self.success_response(
            "Document reviewed successfully",
            data=self._serialize_document(document.sudo()),
        )

    @http.route(
        f"{BASE_URL}/candidate/documents/<int:document_id>/review",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def review_candidate_document(self, document_id, **kwargs):
        return self._review_candidate_document(document_id, **kwargs)

    @http.route(
        f"{BASE_URL}/candidate/documents/<int:document_id>/accept",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def accept_candidate_document(self, document_id, **kwargs):
        return self._review_candidate_document(document_id, status="accepted", **kwargs)

    @http.route(
        f"{BASE_URL}/candidate/documents/<int:document_id>/reject",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def reject_candidate_document(self, document_id, **kwargs):
        return self._review_candidate_document(document_id, status="rejected", **kwargs)

    @http.route(
        f"{BASE_URL}/candidate/documents/<int:document_id>/content",
        auth="public",
        type="http",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    def candidate_document_content(self, document_id, download=False, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self.error_response("Authentication failed", errors=["Login is required"], status=401)

        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not document or not self._can_access_candidate_document(user, document) or not document.attachment_id:
            return self.error_response("Document not found", errors=["No uploaded attachment was found"], status=404)

        attachment = document.attachment_id.sudo()
        raw_content = attachment.raw or b""
        disposition = "attachment" if str(download).lower() in ("1", "true", "yes") else "inline"
        headers = [
            ("Content-Type", attachment.mimetype or "application/octet-stream"),
            ("Content-Length", str(len(raw_content))),
            ("Content-Disposition", content_disposition(
                attachment.name or document.document_type_id.name,
                disposition_type=disposition,
            )),
        ]
        return request.make_response(raw_content, headers)
