# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrCandidate(models.Model):
    _inherit = "hr.candidate"

    candidate_stage = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
        required=True,
    )

    image_1920 = fields.Image("Photo", attachment=True, max_width=1920, max_height=1920)
    khmer_name = fields.Char("Khmer Name", tracking=True)
    english_name = fields.Char("English Name", tracking=True)
    position_name = fields.Char("Position", tracking=True)
    gender = fields.Selection(
        selection=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        tracking=True,
    )
    marital_status = fields.Selection(
        selection=[
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
        ],
        tracking=True,
    )
    date_of_birth = fields.Date("Date of Birth", tracking=True)
    place_of_birth = fields.Text("Place of Birth")
    current_address = fields.Text("Current Address")
    permanent_address = fields.Text("Permanent Address")
    national_id_or_passport = fields.Char("National ID/Passport No.", tracking=True)

    father_name = fields.Char("Father Name")
    father_job = fields.Char("Father Occupation")
    mother_name = fields.Char("Mother Name")
    mother_job = fields.Char("Mother Occupation")
    number_of_siblings = fields.Integer("Number of Siblings")
    family_contact_number = fields.Char("Family Contact Number")
    family_current_address = fields.Text("Family Current Address")
    family_permanent_address = fields.Text("Family Permanent Address")

    spouse_name = fields.Char("Spouse Name")
    spouse_job = fields.Char("Spouse Occupation")
    number_of_children = fields.Integer("Number of Children")
    spouse_contact_number = fields.Char("Spouse Contact Number")
    spouse_current_address = fields.Text("Spouse Current Address")
    spouse_permanent_address = fields.Text("Spouse Permanent Address")

    years_of_study = fields.Char("Years of Study")
    degree_types = fields.Char("Degree Types")
    education_major = fields.Char("Education Major")
    education_notes = fields.Text("Education Notes / Other")

    short_course_certificates = fields.Char("Short-Course Certificates")
    short_course_duration = fields.Char("Short-Course Duration")
    short_course_major = fields.Char("Short-Course Major")
    short_course_notes = fields.Text("Short-Course Notes / Other")

    latest_institution_name = fields.Char("Latest Institution Name")
    employment_history_position = fields.Char("Employment History Position")
    duration_of_work = fields.Char("Duration of Work")
    job_responsibility = fields.Text("Job Responsibility")
    employment_history_notes = fields.Text("Employment History Notes / Other")

    had_injury = fields.Boolean("Had Serious Illness or Injury")
    had_injury_description = fields.Text("Illness / Injury Description")
    arrested = fields.Boolean("Arrested / Convicted / Committed Crimes")
    arrested_description = fields.Text("Crime / Arrest Description")

    declaration_date = fields.Date("Declaration Date")
    declaration_signature = fields.Text("Declaration Signature")

    guarantee_letter = fields.Text("Guarantee Letter", tracking=True)
    conflict_interest = fields.Text("Conflict Interest", tracking=True)
    candidate_form_review_note = fields.Text("Candidate Form Review Note", tracking=True)
    candidate_form_reviewed_by = fields.Many2one("res.users", string="Candidate Form Reviewed By", readonly=True, tracking=True)
    candidate_form_reviewed_on = fields.Datetime("Candidate Form Reviewed On", readonly=True, tracking=True)

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
        for vals in vals_list:
            self._normalize_candidate_identity_vals(vals)
        candidates = super().create(vals_list)
        candidates._ensure_required_document_lines()
        candidates._create_portal_user_if_missing()
        return candidates

    def _create_portal_user_if_missing(self):
        portal_group = self.env.ref("base.group_portal")
        for candidate in self:
            if candidate.portal_user_id:
                continue
            email = candidate.email_from
            if not email:
                continue
            existing_user = self.env["res.users"].sudo().search(
                [("login", "=", email)], limit=1
            )
            if existing_user:
                candidate.portal_user_id = existing_user
                continue
            partner = candidate.partner_id
            if not partner:
                partner = self.env["res.partner"].sudo().create({
                    "name": candidate.partner_name or email,
                    "email": email,
                    "company_type": "person",
                })
            new_user = self.env["res.users"].sudo().with_context(
                no_reset_password=True
            ).create({
                "name": candidate.partner_name or email,
                "login": email,
                "email": email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [portal_group.id])],
                "company_id": candidate.company_id.id or self.env.company.id,
                "company_ids": [(4, candidate.company_id.id or self.env.company.id)],
            })
            candidate.portal_user_id = new_user
            candidate._send_portal_invitation_email(new_user)

    def _send_portal_invitation_email(self, user):
        wizard = self.env["portal.wizard"].sudo().create({"portal_wizard_user_ids": []})
        wizard_user = self.env["portal.wizard.user"].sudo().create({
            "wizard_id": wizard.id,
            "partner_id": user.partner_id.id,
            "email": user.email,
        })
        wizard_user._send_email()

    def write(self, vals):
        self._normalize_candidate_identity_vals(vals)
        result = super().write(vals)
        if {"company_id", "portal_user_id"} & set(vals):
            self._ensure_required_document_lines()
        return result

    @api.model
    def _normalize_candidate_identity_vals(self, vals):
        english_name = vals.get("english_name")
        partner_name = vals.get("partner_name")
        if english_name and not partner_name:
            vals["partner_name"] = english_name
        elif partner_name and not english_name:
            vals["english_name"] = partner_name

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
