# -*- coding: utf-8 -*-

from datetime import datetime
import hashlib
import jwt

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_angkit(cls):
        # Allow OPTIONS request for CORS preflight
        if request.httprequest.method == 'OPTIONS':
            return

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
            if not secret_key:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Server authentication misconfiguration'
                }, status=500)

            # Decode the JWT token with verification
            try:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Token has expired'
                }, status=401)
            except jwt.InvalidTokenError:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Invalid token'
                }, status=401)

            # Check expiration (additional check for safety)
            if payload.get('exp') and payload.get('exp') < int(datetime.utcnow().timestamp()):
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Token has expired'
                }, status=401)

            # Check token revocation: verify the token is still active in the DB.
            # This ensures logout/revocation is respected even within the JWT TTL window.
            hashed_token = hashlib.sha256(token.encode()).hexdigest()
            token_record = request.env['res.user.token'].sudo().search([
                ('access_token', '=', hashed_token),
                ('active', '=', True),
            ], limit=1)
            if not token_record:
                return request.make_json_response({
                    'status': False,
                    'message': 'Authentication failed',
                    'error': 'Token has been revoked or is invalid'
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
        except Exception:
            return request.make_json_response({
                'status': False,
                'message': 'Authentication failed',
                'error': 'Token validation error'
            }, status=401)