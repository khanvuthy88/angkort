# -*- coding: utf-8 -*-

import mimetypes

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CandidateDocumentType(models.Model):
    _name = "angkot.candidate.document.type"
    _description = "Candidate Document Type"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    category = fields.Selection(
        selection=[
            ("identity", "Identity"),
            ("education", "Education"),
            ("banking", "Banking"),
            ("compliance", "Compliance"),
            ("other", "Other"),
        ],
        required=True,
        default="identity",
    )
    required = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
    note = fields.Text()

    _sql_constraints = [
        ("angkot_candidate_document_type_code_uniq", "unique(code)", "The document code must be unique."),
    ]


class CandidateDocument(models.Model):
    _name = "angkot.candidate.document"
    _description = "Candidate Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "document_type_sequence, id"

    candidate_id = fields.Many2one("hr.candidate", required=True, ondelete="cascade", tracking=True)
    company_id = fields.Many2one(related="candidate_id.company_id", store=True, readonly=True)
    portal_user_id = fields.Many2one(related="candidate_id.portal_user_id", store=True, readonly=True)
    officer_user_id = fields.Many2one(related="candidate_id.officer_user_id", store=True, readonly=True)
    manager_user_id = fields.Many2one(related="candidate_id.user_id", store=True, readonly=True)
    document_type_id = fields.Many2one(
        "angkot.candidate.document.type",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    document_type_sequence = fields.Integer(related="document_type_id.sequence", store=True, readonly=True)
    name = fields.Char(compute="_compute_name", store=True)
    category = fields.Selection(related="document_type_id.category", store=True, readonly=True)
    required = fields.Boolean(related="document_type_id.required", store=True, readonly=True)
    status = fields.Selection(
        selection=[
            ("missing", "Missing"),
            ("submitted", "Submitted"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="missing",
        tracking=True,
        required=True,
    )
    attachment_id = fields.Many2one("ir.attachment", string="Attachment", copy=False)
    filename = fields.Char(compute="_compute_attachment_meta", store=True)
    mimetype = fields.Char(compute="_compute_attachment_meta", store=True)
    is_image = fields.Boolean(compute="_compute_attachment_flags")
    is_pdf = fields.Boolean(compute="_compute_attachment_flags")
    upload_date = fields.Datetime(readonly=True, tracking=True)
    reviewed_by = fields.Many2one("res.users", readonly=True, tracking=True)
    reviewed_on = fields.Datetime(readonly=True, tracking=True)
    review_note = fields.Text(tracking=True)

    _sql_constraints = [
        (
            "angkot_candidate_document_candidate_type_uniq",
            "unique(candidate_id, document_type_id)",
            "Each candidate can only have one checklist line per document type.",
        ),
    ]

    @api.depends("candidate_id", "document_type_id")
    def _compute_name(self):
        for document in self:
            parts = [part for part in [document.candidate_id.display_name, document.document_type_id.name] if part]
            document.name = " - ".join(parts)

    @api.depends("attachment_id", "attachment_id.name", "attachment_id.mimetype", "attachment_id.datas_fname")
    def _compute_attachment_meta(self):
        for document in self:
            attachment = document.attachment_id
            document.filename = attachment.datas_fname or attachment.name
            document.mimetype = attachment.mimetype

    @api.depends("mimetype")
    def _compute_attachment_flags(self):
        for document in self:
            document.is_image = bool(document.mimetype and document.mimetype.startswith("image/"))
            document.is_pdf = document.mimetype == "application/pdf"

    @api.model
    def _allowed_portal_mimetypes(self):
        return {
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            "image/bmp",
            "image/tiff",
        }

    def _check_uploadable_file(self, filename, mimetype):
        self.ensure_one()
        effective_mimetype = mimetype or mimetypes.guess_type(filename or "")[0]
        if not effective_mimetype:
            raise ValidationError(_("Unsupported file type. Please upload a PDF or image file."))
        if effective_mimetype not in self._allowed_portal_mimetypes():
            raise ValidationError(_("Only PDF and image files are allowed."))
        return effective_mimetype

    def _replace_attachment(self, filename, content, mimetype, uploaded_by):
        self.ensure_one()
        if not self.candidate_id:
            raise ValidationError(_("The candidate document is not linked to a candidate."))

        effective_mimetype = self._check_uploadable_file(filename, mimetype)
        previous_attachment = self.attachment_id.sudo()
        attachment_vals = {
            "name": "%s - %s" % (self.candidate_id.display_name, self.document_type_id.name),
            "datas_fname": filename,
            "raw": content,
            "mimetype": effective_mimetype,
            "res_model": "hr.candidate",
            "res_id": self.candidate_id.id,
        }
        attachment = self.env["ir.attachment"].sudo().create(attachment_vals)
        self.sudo().write({
            "attachment_id": attachment.id,
            "status": "submitted",
            "upload_date": fields.Datetime.now(),
            "reviewed_by": False,
            "reviewed_on": False,
            "review_note": False,
        })
        if previous_attachment:
            previous_attachment.unlink()
        self.message_post(
            body=_("Document uploaded by %s.") % (uploaded_by.display_name or uploaded_by.name),
            attachment_ids=[attachment.id],
        )
        self.candidate_id.message_post(
            body=_("Document updated: %s") % self.document_type_id.name,
            attachment_ids=[attachment.id],
        )
        return attachment

    def portal_upload_file(self, upload_file, uploaded_by):
        self.ensure_one()
        content = upload_file.read()
        if not content:
            raise ValidationError(_("The uploaded file is empty."))
        filename = upload_file.filename or self.document_type_id.name
        mimetype = getattr(upload_file, "content_type", False)
        return self._replace_attachment(filename, content, mimetype, uploaded_by)

    def action_accept(self):
        for document in self:
            if not document.attachment_id:
                raise ValidationError(_("You cannot accept a document that has no uploaded file."))
            document.write({
                "status": "accepted",
                "reviewed_by": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })

    def action_reject(self):
        for document in self:
            document.write({
                "status": "rejected",
                "reviewed_by": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })

    def action_reset_to_missing(self):
        for document in self:
            attachment = document.attachment_id.sudo()
            document.write({
                "status": "missing",
                "attachment_id": False,
                "upload_date": False,
                "reviewed_by": False,
                "reviewed_on": False,
                "review_note": False,
            })
            if attachment:
                attachment.unlink()

    def action_open_attachment(self):
        self.ensure_one()
        if not self.attachment_id:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.attachment_id.id,
            "target": "new",
        }

    def unlink(self):
        attachments = self.mapped("attachment_id").sudo()
        result = super().unlink()
        if attachments:
            attachments.unlink()
        return result
