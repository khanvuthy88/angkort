# -*- coding: utf-8 -*-

from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """
        Override session_info to add custom fields for recruitment user roles.
        """
        result = super(Http, self).session_info()
        
        # Add custom fields for recruitment groups
        user = self.env.user
        session_uid = self.env.context.get('uid')
        
        if session_uid:
            result.update({
                'is_applicant': user.has_group('angkot_recruitement.group_hr_recruitment_applicant'),
                'is_employer': user.has_group('angkot_recruitement.group_hr_recruitment_officer'),
            })
        else:
            result.update({
                'is_applicant': False,
                'is_employer': False,
            })
        
        return result

