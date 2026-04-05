# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrCandidate(models.Model):
    _inherit = "hr.candidate"

    portal_user_id = fields.Many2one(
        "res.users",
        string="Candidate User",
        domain="[('share', '=', True)]",
        tracking=True,
        help="Portal user allowed to upload and replace this candidate's documents.",
    )
    officer_user_id = fields.Many2one(
        "res.users",
        string="Encharge Officer",
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
    )
    document_ids = fields.One2many(
        "angkot.candidate.document",
        "candidate_id",
        string="Document Checklist",
    )
    document_count = fields.Integer(
        string="Documents",
        compute="_compute_document_progress",
    )
    accepted_document_count = fields.Integer(
        string="Accepted Documents",
        compute="_compute_document_progress",
    )
    submitted_document_count = fields.Integer(
        string="Submitted Documents",
        compute="_compute_document_progress",
    )
    required_document_count = fields.Integer(
        string="Required Documents",
        compute="_compute_document_progress",
    )

    @api.depends("document_ids.status", "document_ids.document_type_id.required")
    def _compute_document_progress(self):
        for candidate in self:
            docs = candidate.document_ids
            required_docs = docs.filtered(lambda doc: doc.document_type_id.required)
            candidate.document_count = len(docs)
            candidate.accepted_document_count = len(docs.filtered(lambda doc: doc.status == "accepted"))
            candidate.submitted_document_count = len(docs.filtered(lambda doc: doc.status == "submitted"))
            candidate.required_document_count = len(required_docs)

    @api.model_create_multi
    def create(self, vals_list):
        candidates = super().create(vals_list)
        candidates._ensure_required_document_lines()
        return candidates

    def write(self, vals):
        result = super().write(vals)
        if {"company_id", "portal_user_id"} & set(vals):
            self._ensure_required_document_lines()
        return result

    def _ensure_required_document_lines(self):
        document_type_model = self.env["angkot.candidate.document.type"]
        document_model = self.env["angkot.candidate.document"]
        doc_types = document_type_model.search([("active", "=", True)])
        for candidate in self:
            existing_type_ids = set(candidate.document_ids.mapped("document_type_id").ids)
            missing_vals = []
            for document_type in doc_types:
                if document_type.id not in existing_type_ids:
                    missing_vals.append({
                        "candidate_id": candidate.id,
                        "document_type_id": document_type.id,
                    })
            if missing_vals:
                document_model.create(missing_vals)

    def action_open_candidate_documents(self):
        self.ensure_one()
        self._ensure_required_document_lines()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "angkot_candidate.action_angkot_candidate_document"
        )
        action["domain"] = [("candidate_id", "=", self.id)]
        action["context"] = {
            "default_candidate_id": self.id,
            "search_default_group_by_category": 1,
        }
        return action

    def action_open_candidate_portal_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/my/candidate/documents",
            "target": "self",
        }
