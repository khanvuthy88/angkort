# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_view_candidate_record(self):
        """View the original candidate record from a candidate contact."""
        self.ensure_one()
        
        # Extract candidate ID from comment
        if not self.comment or 'Original candidate ID:' not in self.comment:
            raise UserError(_('This contact was not created from a candidate record.'))
        
        try:
            # Extract candidate ID from comment
            candidate_id_line = [line for line in self.comment.split('\n') if 'Original candidate ID:' in line][0]
            candidate_id = int(candidate_id_line.split('Original candidate ID:')[1].strip())
            
            # Find the candidate
            candidate = self.env['hr.candidate'].browse(candidate_id)
            if not candidate.exists():
                raise UserError(_('The original candidate record no longer exists.'))
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Original Candidate'),
                'res_model': 'hr.candidate',
                'res_id': candidate.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except (ValueError, IndexError):
            raise UserError(_('Could not find the original candidate ID in the contact record.'))
