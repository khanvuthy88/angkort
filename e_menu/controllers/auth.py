from datetime import datetime, timedelta
import hashlib
from functools import wraps

import jwt

from odoo import http
from odoo.http import request, route
from odoo.tools import config


def validate_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the Authorization header
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {"error": "Missing or invalid Authorization header"}, 401

        # Extract the token
        token = auth_header.split(' ')[1]

        try:
            secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            # Decode the JWT token
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])

            # Check expiration
            if payload.get('exp') < int(datetime.utcnow().timestamp()):
                return {"error": "Token has expired"}, 401

            # Fetch the user from the database
            user_id = payload.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"error": "Invalid token"}, 401

            # Pass the user object to the controller method
            kwargs['user'] = user
            return func(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            return {"error": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401

    return wrapper


class Authentication(http.Controller):

    def _get_system_secret_key(self):
        return request.env['ir.config_parameter'].sudo().get_param('database.secret')

    @validate_token
    @route("/api/test", type="json", auth="none", cors="http://localhost:8067", methods=["POST"])
    def test(self, **kw):
        return kw

    @route('/api/login', type='json', auth='none', methods=['POST'])
    def login(self, **kw):
        """Login and generate tokens."""
        data = request.get_json_data()
        username = data.get('username')
        password = data.get('password')
        # Authenticate the user
        user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
        if not user:
            return {"error": "Invalid username or password"}

        db = config['db_name']
        credential = {'login': username, 'password': password, 'type': 'password'}
        uid = request.session.authenticate(db, credential)
        if not uid:
            return {'error': "Invalid username or password"}

        # Generate tokens
        access_token = self._generate_token(user.id, 'access', minutes=5)
        refresh_token = self._generate_token(user.id, 'refresh', days=7)

        # Store tokens in the database
        token_model = request.env['res.user.token'].sudo()
        token_model.create_token(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_expiry=datetime.utcnow() + timedelta(minutes=30),
            refresh_expiry=datetime.utcnow() + timedelta(days=7)
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 1800  # 30 minutes in seconds
        }

    @route('/api/refresh', type='json', auth='none', methods=['POST'])
    def refresh_token(self, **kwargs):
        """Generate a new access token using a refresh token."""
        request_data = request.get_json_data()
        refresh_token = request_data.get('refresh_token')
        token_model = request.env['res.user.token'].sudo()
        user_id = token_model.validate_token(refresh_token, token_type='refresh')

        if not user_id:
            return {"error": "Invalid or expired refresh token"}

        # Generate a new access token
        new_access_token = self._generate_token(user_id, 'access', minutes=30)

        # Update the database with the new token
        token_model.create_token(
            user_id=user_id,
            access_token=new_access_token,
            refresh_token=refresh_token,
            access_expiry=datetime.utcnow() + timedelta(minutes=30),
            refresh_expiry=datetime.utcnow() + timedelta(days=7)  # Keep refresh expiry unchanged
        )

        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 1800  # 30 minutes in seconds
        }

    @route('/api/logout', type='json', auth='none', methods=['POST'])
    def logout(self, **kwargs):
        """Revoke tokens for logout."""
        access_token = kwargs.get('access_token')
        token_model = request.env['auth.token'].sudo()
        token = token_model.search([('access_token', '=', hashlib.sha256(access_token.encode()).hexdigest())], limit=1)

        if token:
            token.active = False
            return {"message": "Successfully logged out"}

        return {"error": "Invalid access token"}

    def _generate_token(self, user_id, token_type, minutes=0, days=0):
        """Generate JWT tokens."""
        payload = {
            "user_id": user_id,
            "type": token_type,
            "exp": datetime.utcnow() + timedelta(minutes=minutes, days=days)
        }
        secret_key = self._get_system_secret_key()
        return jwt.encode(payload, secret_key, algorithm="HS256")
