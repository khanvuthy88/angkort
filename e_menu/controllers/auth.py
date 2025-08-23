from datetime import datetime, timedelta
import hashlib
import json
import logging
from functools import wraps

import jwt

from odoo import http
from odoo.http import request, route, Response
from odoo.tools import config

_logger = logging.getLogger(__name__)


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

    @route('/api/test', type='http', cors="*", csrf=False, auth='none', methods=['GET', 'POST'])
    def test_http(self, **kw):
        """
        Simple test endpoint for HTTP requests.
        
        Endpoint: GET/POST /angkort/api/v1/test
        Auth: None (public endpoint)
        
        Returns:
            HTTP Response with JSON content containing request information
        """
        try:
            # Get request information
            method = request.httprequest.method
            headers = dict(request.httprequest.headers)
            content_type = headers.get('Content-Type', '')
            
            # Parse request data
            data = {}
            if method == 'POST':
                if 'application/json' in content_type and request.httprequest.data:
                    try:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        data = {"error": "Invalid JSON"}
                else:
                    data = dict(request.httprequest.form)
            
            response_data = {
                "status": True,
                "message": "Test endpoint working",
                "method": method,
                "content_type": content_type,
                "headers": headers,
                "data": data,
                "form_data": dict(request.httprequest.form),
                "raw_data": request.httprequest.data.decode('utf-8') if request.httprequest.data else None
            }
            
            return Response(
                json.dumps(response_data, indent=2),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Test endpoint error: {str(e)}")
            
            return Response(
                json.dumps({
                    "status": False,
                    "message": "Test endpoint error",
                    "error": str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @route('/angkort/api/v1/login', type='http', cors="*", csrf=False, auth='none', methods=['POST'])
    def login(self, **kw):
        """
        Login and generate tokens.
        
        Endpoint: POST /angkort/api/v1/login
        Auth: None (public endpoint)
        Content-Type: application/json
        
        Request Body:
            {
                "username": str,  # Required: User's login username/email
                "password": str    # Required: User's password
            }
            
        Returns:
            HTTP Response with JSON content containing:
                - Success (200): User info and tokens
                - Error (400): Invalid request data
                - Error (401): Authentication failed
                - Error (500): Server error
        """
        try:
            # Parse JSON data from request body
            try:
                if request.httprequest.data:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    # Fallback to form data if no JSON body
                    data = dict(request.httprequest.form)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Invalid JSON format",
                        "error": str(e)
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Validate required fields
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Missing required fields",
                        "error": "Username and password are required"
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Authenticate the user
            user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
            if not user:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Authentication failed",
                        "error": "Invalid username or password"
                    }),
                    status=401,
                    content_type='application/json'
                )
            
            # Verify password using Odoo's authentication system
            db = config['db_name']
            credential = {'login': username, 'password': password, 'type': 'password'}
            
            try:
                uid = request.session.authenticate(db, credential)
                if not uid:
                    return Response(
                        json.dumps({
                            "status": False,
                            "message": "Authentication failed",
                            "error": "Invalid username or password"
                        }),
                        status=401,
                        content_type='application/json'
                    )
            except Exception as auth_error:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Authentication failed",
                        "error": "Invalid credentials"
                    }),
                    status=401,
                    content_type='application/json'
                )
            
            # Generate tokens
            access_token = self._generate_token(user.id, 'access', minutes=30)
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
            
            # Prepare success response
            response_data = {
                "status": True,
                "message": "Login successful",
                "data": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 1800,  # 30 minutes in seconds
                    "user_id": user.id,
                    "username": user.login,
                    "name": user.name,
                    "email": user.email,
                    'is_merchant': request.env.user.has_group("e_menu.group_merchant"),
                    'is_admin': request.env.user.has_group("base.group_system"),
                }
            }
            
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            # Log the error for debugging
            _logger.error(f"Login error: {str(e)}")
            
            return Response(
                json.dumps({
                    "status": False,
                    "message": "Internal server error",
                    "error": "An unexpected error occurred during login"
                }),
                status=500,
                content_type='application/json'
            )

    @route('/angkort/api/v1/refresh', type='http', cors="*", csrf=False, auth='none', methods=['POST'])
    def refresh_token(self, **kwargs):
        """
        Generate a new access token using a valid refresh token.

        Endpoint: POST /angkort/api/v1/refresh
        Auth: None (public endpoint)
        Content-Type: application/json

        Request Body:
            {
                "refresh_token": str  # Required: The refresh token to generate new access token
            }

        Returns:
            HTTP Response with JSON content containing:
                - Success (200): New access token details
                - Error (400): Invalid request data
                - Error (401): Invalid or expired refresh token
                - Error (500): Server error

        Status Codes:
            200: New access token generated successfully
            400: Invalid request or refresh token
            401: Invalid or expired refresh token
            500: Server error
        """
        try:
            # Check Content-Type header
            content_type = request.httprequest.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Invalid request format",
                        "error": "Content-Type must be application/json"
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Parse JSON data from request body
            try:
                if request.httprequest.data:
                    request_data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    # Fallback to form data if no JSON body
                    request_data = dict(request.httprequest.form)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Invalid JSON format",
                        "error": str(e)
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Validate required fields
            refresh_token = request_data.get('refresh_token')
            if not refresh_token:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Missing required field",
                        "error": "Refresh token is required"
                    }),
                    status=400,
                    content_type='application/json'
                )
            
            # Validate the refresh token
            token_model = request.env['res.user.token'].sudo()
            user_id = token_model.validate_token(refresh_token, token_type='refresh')

            if not user_id:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Authentication failed",
                        "error": "Invalid or expired refresh token"
                    }),
                    status=401,
                    content_type='application/json'
                )

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

            # Prepare success response
            response_data = {
                "status": True,
                "message": "Token refreshed successfully",
                "data": {
                    "access_token": new_access_token,
                    "token_type": "Bearer",
                    "expires_in": 1800  # 30 minutes in seconds
                }
            }

            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            # Log the error for debugging
            _logger.error(f"Token refresh error: {str(e)}")
            
            return Response(
                json.dumps({
                    "status": False,
                    "message": "Internal server error",
                    "error": "An unexpected error occurred during token refresh"
                }),
                status=500,
                content_type='application/json'
            )

    @route('/angkort/api/v1/logout', auth="angkit", type="http", methods=["POST"], csrf=False, cors="*")
    def logout(self, **kwargs):
        """
        Logout a user by invalidating their access token.

        Endpoint: POST /angkort/api/v1/logout
        Auth: Required (angkit)
        Content-Type: application/json

        Headers:
            Authorization: Bearer <access_token>  # Required: The user's access token

        Returns:
            HTTP Response with JSON content containing:
                - Success (200): Logout confirmation
                - Error (400): Access token missing
                - Error (401): Invalid access token
                - Error (500): Server error

        Status Codes:
            200: Successfully logged out
            400: Access token missing
            401: Invalid access token
            500: Server error
        """
        try:
            access_token_header = request.httprequest.headers.get('Authorization')
            if not access_token_header:
                return Response(
                    json.dumps({
                        "status": False,
                        "message": "Access token missing",
                        "error": "Authorization header is required"
                    }),
                    status=400,
                    content_type='application/json'
                )

            if access_token_header.startswith('Bearer '):
                access_token_header = access_token_header[7:]

            # Use the correct token model
            token_model = request.env['res.user.token'].sudo()
            token = token_model.search([('access_token', '=', hashlib.sha256(access_token_header.encode()).hexdigest())], limit=1)

            if token:
                token.write({
                    'active': False
                })
                request.session.logout(keep_db=True)
                return Response(
                    json.dumps({
                        "status": True,
                        "message": "Successfully logged out"
                    }),
                    status=200,
                    content_type='application/json'
                )

            return Response(
                json.dumps({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid access token"
                }),
                status=401,
                content_type='application/json'
            )
            
        except Exception as e:
            # Log the error for debugging
            _logger.error(f"Logout error: {str(e)}")
            
            return Response(
                json.dumps({
                    "status": False,
                    "message": "Internal server error",
                    "error": "An unexpected error occurred during logout"
                }),
                status=500,
                content_type='application/json'
            )

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
