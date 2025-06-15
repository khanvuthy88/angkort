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
            print(payload)
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
        access_token = self._generate_token(user.id, 'access', minutes=30)
        print(access_token)
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
        """
        Generate a new access token using a valid refresh token.

        Endpoint: POST /api/refresh
        Auth: None (public endpoint)
        Content-Type: application/json

        Request Body:
            {
                "refresh_token": str  # Required: The refresh token to generate new access token
            }

        Returns:
            dict: Response containing new access token details
                {
                    "access_token": str,    # The newly generated access token
                    "token_type": str,      # Always "Bearer"
                    "expires_in": int       # Token expiration time in seconds (1800 = 30 minutes)
                }

        Error Response:
            {
                "error": str  # Error message if refresh token is invalid or expired
            }

        Status Codes:
            200: New access token generated successfully
            400: Invalid request or refresh token

        Example Request:
            {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }

        Example Response:
            {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 1800
            }
        """
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

    @route('/api/logout', auth="angkit", type="http", methods=["POST"], csrf=False, cors="*")
    def logout(self, **kwargs):
        """
        Logout a user by invalidating their access token.

        Endpoint: POST /api/logout
        Auth: Required (angkit)
        Content-Type: application/json

        Headers:
            Authorization: Bearer <access_token>  # Required: The user's access token

        Returns:
            dict: Response containing status message
                {
                    'message': str  # Success or error message
                }

        Status Codes:
            200: Successfully logged out
            400: Access token missing
            401: Invalid access token

        Example Response (Success):
            {
                "message": "Successfully logged out"
            }

        Example Response (Error):
            {
                "message": "Access token missing"
            }
            or
            {
                "error": "Invalid access token"
            }
        """
        access_token_header = request.httprequest.headers.get('Authorization')
        if not access_token_header:
            return request.make_json_response({'message': 'Access token missing'}, status=400)

        if access_token_header.startswith('Bearer '):
            access_token_header = access_token_header[7:]

        token_model = request.env['auth.token'].sudo()
        token = token_model.search([('access_token', '=', hashlib.sha256(access_token_header.encode()).hexdigest())], limit=1)

        if token:
            token.write({
                'active': False
            })
            request.session.logout(keep_db=True)
            return request.make_json_response({'message': 'Successfully logged out'}, status=200)

        return request.make_json_response({'error': 'Invalid access token'}, status=401)

    def _generate_token(self, user_id, token_type, minutes=0, days=0):
        """
        Generate a JWT token for user authentication.

        Args:
            user_id (int): The ID of the user to generate the token for
            token_type (str): The type of token to generate (e.g., 'access', 'refresh')
            minutes (int, optional): Token expiration time in minutes. Defaults to 0.
            days (int, optional): Token expiration time in days. Defaults to 0.

        Returns:
            str: The generated JWT token

        Note:
            - The token expiration time is calculated as current time + minutes + days
            - The token is signed using HS256 algorithm
            - The secret key is retrieved from system parameters
            - Token payload includes:
                - user_id: The ID of the user
                - type: The type of token
                - exp: Expiration timestamp

        Example:
            >>> _generate_token(1, 'access', minutes=30)  # Token expires in 30 minutes
            >>> _generate_token(1, 'refresh', days=7)     # Token expires in 7 days
        """
        payload = {
            "user_id": user_id,
            "type": token_type,
            "exp": datetime.utcnow() + timedelta(minutes=minutes, days=days)
        }
        secret_key = self._get_system_secret_key()
        return jwt.encode(payload, secret_key, algorithm="HS256")
