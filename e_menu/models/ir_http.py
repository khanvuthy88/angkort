# -*- coding: utf-8 -*-

from datetime import datetime
import jwt
from werkzeug.exceptions import BadRequest

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_angkit(cls):
        print("JWT Auth - _auth_method_angkit called")
        # Get the Authorization header
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return request.make_json_response({
                'status': False,
                'message': 'Authentication failed',
                'error': 'Missing or invalid Authorization header'
            }, status=401)

        # Extract the token
        token = auth_header.split(' ')[1]

        try:
            secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            
            # Decode the JWT token with verification
            try:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                print(f"JWT Auth - Token decoded successfully: {payload}")
            except jwt.ExpiredSignatureError as e:
                print(f"JWT Auth - Token expired: {str(e)}")
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Token has expired'
                }, status=401)
            except jwt.InvalidTokenError as e:
                print(f"JWT Auth - Invalid token: {str(e)}")
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Invalid token'
                }, status=401)

            # Check expiration (additional check for safety)
            if payload.get('exp') and payload.get('exp') < int(datetime.utcnow().timestamp()):
                print("JWT Auth - Token expired (additional check)")
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Token has expired'
                }, status=401)

            # Fetch the user from the database
            user_id = payload.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Invalid token'
                }, status=401)

            # Set the user context using update_env
            request.update_env(user=user_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return request.make_json_response({
                'status': False,
                'message': 'Authentication failed',
                'error': 'Token validation error'
            }, status=401)