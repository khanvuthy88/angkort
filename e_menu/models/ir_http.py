# -*- coding: utf-8 -*-

from datetime import datetime
import hashlib
import jwt
import werkzeug.exceptions

from odoo import fields, models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _abort_with_json(cls, status, msg):
        import json
        from werkzeug.exceptions import HTTPException
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization',
        }
        body = json.dumps({'status': False, 'message': 'Authentication failed', 'error': msg})
        response = request.make_response(body, headers=headers)
        response.status_code = status
        raise HTTPException(response=response)

    @classmethod
    def _bearer_authenticate(cls):
        # Allow OPTIONS request for CORS preflight
        if request.httprequest.method == 'OPTIONS':
            return

        # Get the Authorization header
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            cls._abort_with_json(401, 'Missing or invalid Authorization header')

        # Extract the token
        token = auth_header.split(' ')[1]

        try:
            secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            if not secret_key:
                cls._abort_with_json(500, 'Server authentication misconfiguration')

            # Decode the JWT token with verification
            try:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                cls._abort_with_json(401, 'Token has expired')
            except jwt.InvalidTokenError:
                cls._abort_with_json(401, 'Invalid token')

            # Check expiration (additional check for safety)
            if payload.get('exp') and payload.get('exp') < int(datetime.utcnow().timestamp()):
                cls._abort_with_json(401, 'Token has expired')

            # Check token revocation: verify the token is still active in the DB.
            # This ensures logout/revocation is respected even within the JWT TTL window.
            hashed_token = hashlib.sha256(token.encode()).hexdigest()
            token_record = request.env['res.user.token'].sudo().search([
                ('access_token', '=', hashed_token),
                ('active', '=', True),
            ], limit=1)
            if not token_record:
                cls._abort_with_json(401, 'Token has been revoked or is invalid')

            # Fetch the user from the database
            user_id = payload.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                cls._abort_with_json(401, 'Invalid token')

            if payload.get('token_type') != 'access':
                cls._abort_with_json(401, 'Invalid token type')

            if token_record.user_id.id != user.id:
                cls._abort_with_json(401, 'Token user mismatch')

            if token_record.expires_at and token_record.expires_at <= fields.Datetime.now():
                cls._abort_with_json(401, 'Token has expired')

            # Set the user context using update_env
            request.update_env(user=user_id)
        except werkzeug.exceptions.HTTPException:
            raise
        except Exception as exc:
            cls._abort_with_json(401, 'Token validation error')

    @classmethod
    def _auth_method_angkit(cls):
        return cls._bearer_authenticate()

    @classmethod
    def _auth_method_core_access(cls):
        return cls._bearer_authenticate()
