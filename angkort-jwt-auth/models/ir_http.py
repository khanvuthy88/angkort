# -*- coding: utf-8 -*-

from werkzeug.exceptions import BadRequest

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_angkort_jwt(cls):
        access_token = request.httprequest.headers.get('Authorization')
        if not access_token:
            return request.make_json_response({
                'status': False,
                'message': 'Authentication failed',
                'error': 'Access token missing'
            }, status=401)

        if access_token.startswith('Bearer '):
            access_token = access_token[7:]

        user_id = request.env["res.users.apikeys"]._check_credentials(scope='rpc', key=access_token)
        if not user_id:
            return request.make_json_response({
                'status': False,
                'message': 'Authentication failed',
                'error': 'Access token invalid'
            }, status=401)

        # take the identity of the API key user
        request.update_env(user=user_id)

        # switch to the user context
        request.update_context(**request.env.user.context_get())