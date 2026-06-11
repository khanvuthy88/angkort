# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    candidate_role = fields.Selection(
        selection=[
            ('none', 'None'),
            ('candidate', 'Candidate'),
            ('general', 'Candidate (General Staff)'),
            ('finance', 'Candidate (Finance Staff)'),
        ],
        string='Candidate Role',
        compute='_compute_candidate_role',
        inverse='_inverse_candidate_role',
    )

    @api.depends('groups_id')
    def _compute_candidate_role(self):
        group_portal = self.env.ref('angkot_candidate.group_candidate_portal')
        group_general = self.env.ref('angkot_candidate.group_candidate_general_staff')
        group_finance = self.env.ref('angkot_candidate.group_candidate_finance_staff')
        for user in self:
            if group_finance in user.groups_id:
                user.candidate_role = 'finance'
            elif group_general in user.groups_id:
                user.candidate_role = 'general'
            elif group_portal in user.groups_id:
                user.candidate_role = 'candidate'
            else:
                user.candidate_role = 'none'

    def _inverse_candidate_role(self):
        group_portal = self.env.ref('angkot_candidate.group_candidate_portal')
        group_general = self.env.ref('angkot_candidate.group_candidate_general_staff')
        group_finance = self.env.ref('angkot_candidate.group_candidate_finance_staff')
        role_map = {
            'candidate': group_portal,
            'general': group_general,
            'finance': group_finance,
        }
        for user in self:
            cmds = [(3, g.id) for g in (group_portal, group_general, group_finance)]
            target = role_map.get(user.candidate_role)
            if target:
                cmds.append((4, target.id))
            user.sudo().write({'groups_id': cmds})
