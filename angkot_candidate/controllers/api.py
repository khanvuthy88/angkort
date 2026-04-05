# -*- coding: utf-8 -*-

import hashlib
import jwt

from odoo import fields, http
from odoo.http import content_disposition, request


BASE_URL = "/angkort/api/v1"


class CandidateDocumentApi(http.Controller):

    @http.route(f"{BASE_URL}/candidate/documents/<path:subpath>", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    @http.route(f"{BASE_URL}/candidate/documents", auth="none", type="http", methods=["OPTIONS"], csrf=False, cors="*")
    def candidate_documents_options(self, subpath=None, **kwargs):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
            "Access-Control-Max-Age": "86400",
        }
        return request.make_response("", headers=headers)

    def _json_error(self, message, *, error=None, status=400):
        payload = {
            "status": False,
            "message": message,
        }
        if error:
            payload["error"] = error
        return request.make_json_response(payload, status=status)

    def _json_success(self, message, data=None, *, status=200):
        payload = {
            "status": True,
            "message": message,
        }
        if data is not None:
            payload["data"] = data
        return request.make_json_response(payload, status=status)

    def _get_bearer_user(self):
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return request.env["res.users"]

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return request.env["res.users"]

        if not request.env.registry.get("res.user.token"):
            return request.env["res.users"]

        secret_key = request.env["ir.config_parameter"].sudo().get_param("database.secret")
        if not secret_key:
            return request.env["res.users"]

        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return request.env["res.users"]

        if payload.get("token_type") != "access":
            return request.env["res.users"]

        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        token_record = request.env["res.user.token"].sudo().search([
            ("access_token", "=", hashed_token),
            ("active", "=", True),
        ], limit=1)
        if not token_record:
            return request.env["res.users"]
        if token_record.expires_at and token_record.expires_at <= fields.Datetime.now():
            return request.env["res.users"]

        user = request.env["res.users"].sudo().browse(payload.get("user_id"))
        return user if user.exists() and token_record.user_id.id == user.id else request.env["res.users"]

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
            "view_url": "/angkort/api/v1/candidate/documents/%s/content" % document.id if attachment else "",
        }

    @http.route(f"{BASE_URL}/candidate/documents", auth="public", type="http", methods=["GET"], csrf=False, cors="*")
    def candidate_documents(self, **kwargs):
        user = self._get_authenticated_user()
        if not user or not user.exists():
            return self._json_error("Authentication failed", error="Login is required", status=401)

        candidate = self._get_candidate_for_user(user)
        if not candidate:
            return self._json_error("Candidate not found", error="No candidate is linked to this user", status=404)

        candidate._ensure_required_document_lines()
        documents = candidate.document_ids.sorted(key=lambda doc: (doc.document_type_sequence, doc.id))
        data = {
            "candidate_id": candidate.id,
            "candidate_name": candidate.display_name,
            "required_document_count": candidate.required_document_count,
            "submitted_document_count": candidate.submitted_document_count,
            "accepted_document_count": candidate.accepted_document_count,
            "documents": [self._serialize_document(document) for document in documents],
        }
        return self._json_success("Candidate documents fetched successfully", data=data)

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
            return self._json_error("Authentication failed", error="Login is required", status=401)

        candidate = self._get_candidate_for_user(user)
        if not candidate:
            return self._json_error("Candidate not found", error="No candidate is linked to this user", status=404)

        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not document or document.candidate_id.id != candidate.id:
            return self._json_error("Document not found", error="The requested document does not belong to the current candidate", status=404)

        upload_file = request.httprequest.files.get("file")
        if not upload_file or not upload_file.filename:
            return self._json_error("Missing required file", error="Field 'file' is required", status=400)

        try:
            document.portal_upload_file(upload_file, user)
        except Exception as error:
            return self._json_error("Upload failed", error=str(error), status=400)

        return self._json_success(
            "Document uploaded successfully",
            data=self._serialize_document(document.sudo()),
            status=201,
        )

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
            return self._json_error("Authentication failed", error="Login is required", status=401)

        candidate = self._get_candidate_for_user(user)
        if not candidate:
            return self._json_error("Candidate not found", error="No candidate is linked to this user", status=404)

        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not document or document.candidate_id.id != candidate.id or not document.attachment_id:
            return self._json_error("Document not found", error="No uploaded attachment was found", status=404)

        attachment = document.attachment_id.sudo()
        raw_content = attachment.raw or b""
        disposition = "attachment" if str(download).lower() in ("1", "true", "yes") else "inline"
        headers = [
            ("Content-Type", attachment.mimetype or "application/octet-stream"),
            ("Content-Length", str(len(raw_content))),
            ("Content-Disposition", content_disposition(
                attachment.datas_fname or attachment.name or document.document_type_id.name,
                disposition_type=disposition,
            )),
        ]
        return request.make_response(raw_content, headers)
