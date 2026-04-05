# -*- coding: utf-8 -*-

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.utils import redirect

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import content_disposition, request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CandidatePortal(CustomerPortal):

    def _get_current_candidate(self):
        return request.env["hr.candidate"].sudo().search(
            [("portal_user_id", "=", request.env.user.id)],
            limit=1,
        )

    def _get_document_grouped_values(self, candidate):
        selection = dict(request.env["angkot.candidate.document.type"]._fields["category"].selection)
        grouped = []
        for key, label in selection.items():
            documents = candidate.document_ids.filtered(lambda doc: doc.category == key).sorted(
                key=lambda doc: (doc.document_type_sequence, doc.id)
            )
            if not documents:
                continue
            grouped.append({
                "key": key,
                "label": label,
                "documents": documents,
                "accepted_count": len(documents.filtered(lambda doc: doc.status == "accepted")),
                "required_count": len(documents.filtered(lambda doc: doc.required)),
            })
        return grouped

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        candidate = self._get_current_candidate()
        if "candidate_document_count" in counters:
            values["candidate_document_count"] = candidate.required_document_count if candidate else 0
        if "candidate_submitted_document_count" in counters:
            values["candidate_submitted_document_count"] = candidate.submitted_document_count if candidate else 0
        return values

    @http.route("/my/candidate/documents", type="http", auth="user", website=True)
    def portal_candidate_documents(self, **kwargs):
        candidate = self._get_current_candidate()
        if not candidate:
            return redirect("/my")

        candidate._ensure_required_document_lines()
        flash_message = request.session.pop("angkot_candidate_flash_message", False)
        flash_level = request.session.pop("angkot_candidate_flash_level", "info")

        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "candidate_documents",
            "candidate": candidate,
            "document_groups": self._get_document_grouped_values(candidate),
            "flash_message": flash_message,
            "flash_level": flash_level,
        })
        return request.render("angkot_candidate.portal_candidate_documents", values)

    @http.route(
        "/my/candidate/documents/<int:document_id>/upload",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def portal_candidate_document_upload(self, document_id, **post):
        candidate = self._get_current_candidate()
        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not candidate or not document or document.candidate_id != candidate:
            raise Forbidden()

        upload_file = request.httprequest.files.get("file")
        if not upload_file or not upload_file.filename:
            request.session["angkot_candidate_flash_message"] = _("Please choose a PDF or image file before uploading.")
            request.session["angkot_candidate_flash_level"] = "danger"
            return redirect("/my/candidate/documents")

        try:
            document.portal_upload_file(upload_file, request.env.user)
            request.session["angkot_candidate_flash_message"] = _("%s uploaded successfully.") % document.document_type_id.name
            request.session["angkot_candidate_flash_level"] = "success"
        except ValidationError as error:
            request.session["angkot_candidate_flash_message"] = error.args[0]
            request.session["angkot_candidate_flash_level"] = "danger"
        return redirect("/my/candidate/documents")

    @http.route(
        "/my/candidate/documents/<int:document_id>/content",
        type="http",
        auth="user",
        website=True,
    )
    def portal_candidate_document_content(self, document_id, download=False, **kwargs):
        candidate = self._get_current_candidate()
        document = request.env["angkot.candidate.document"].sudo().browse(document_id).exists()
        if not candidate or not document or document.candidate_id != candidate:
            raise Forbidden()
        if not document.attachment_id:
            raise NotFound()

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
