from odoo import fields, http
from odoo.http import request, route, Response
import jwt
from datetime import datetime, timedelta
import hashlib
import json
import logging
from .utils import BASE_URL

_logger = logging.getLogger(__name__)

class AuthMixin:
    def _generate_token(self, user_id, token_type, minutes=0, days=0):
        """
        Generate a JWT token for the user.

        Args:
            user_id (int): User ID
            token_type (str): Type of token ('access' or 'refresh')
            minutes (int): Token expiry in minutes
            days (int): Token expiry in days

        Returns:
            str: Generated JWT token
        """
        # Calculate expiry time
        expiry = datetime.utcnow()
        if days > 0:
            expiry += timedelta(days=days)
        if minutes > 0:
            expiry += timedelta(minutes=minutes)

        # Create payload
        payload = {
            'user_id': user_id,
            'token_type': token_type,
            'exp': expiry,
            'iat': datetime.utcnow()
        }

        # Get secret key from Odoo configuration
        secret_key = request.env['ir.config_parameter'].sudo().get_param('database.secret', 'your-secret-key-here')
        token = jwt.encode(payload, secret_key, algorithm='HS256')

        return token

    def _validate_token(self, token, token_type='access'):
        """
        Validate an access or refresh token.

        Args:
            token (str): The token to validate
            token_type (str): Type of token ('access' or 'refresh')

        Returns:
            int or False: User ID if valid, False otherwise
        """
        # Hash the token for database search
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # Search for the token in the database
        token_model = request.env['res.user.token'].sudo()
        domain = [
            ('access_token' if token_type == 'access' else 'refresh_token', '=', hashed_token),
            ('active', '=', True)
        ]
        
        token_record = token_model.search(domain, limit=1)
        
        if token_record:
            # Check if token is not expired
            expiry_field = 'expires_at' if token_type == 'access' else 'refresh_expires_at'
            if fields.Datetime.now() < token_record[expiry_field]:
                return token_record.user_id.id
        
        return False

    def _get_user_from_token(self, token, token_type='access'):
        """
        Get user object from a valid token.

        Args:
            token (str): The token to validate
            token_type (str): Type of token ('access' or 'refresh')

        Returns:
            res.users or None: User object if valid, None otherwise
        """
        user_id = self._validate_token(token, token_type)
        if user_id:
            return request.env['res.users'].sudo().browse(user_id)
        return None

    def _revoke_all_user_tokens(self, user_id):
        """
        Revoke all active tokens for a specific user.

        Args:
            user_id (int): The ID of the user whose tokens should be revoked

        Returns:
            bool: True if tokens were revoked, False otherwise
        """
        try:
            token_model = request.env['res.user.token'].sudo()
            active_tokens = token_model.search([
                ('user_id', '=', user_id),
                ('active', '=', True)
            ])
            
            if active_tokens:
                active_tokens.write({
                    'active': False,
                    'deactivated_at': fields.Datetime.now()
                })
                return True
            return False
        except Exception:
            return False

    def _get_token_info(self, token, token_type='access'):
        """
        Get detailed information about a token.

        Args:
            token (str): The token to get information for
            token_type (str): Type of token ('access' or 'refresh')

        Returns:
            dict or None: Token information if valid, None otherwise
        """
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        token_model = request.env['res.user.token'].sudo()
        
        domain = [
            ('access_token' if token_type == 'access' else 'refresh_token', '=', hashed_token),
            ('active', '=', True)
        ]
        
        token_record = token_model.search(domain, limit=1)
        
        if token_record:
            expiry_field = 'expires_at' if token_type == 'access' else 'refresh_expires_at'
            remaining = token_record[expiry_field] - fields.Datetime.now()
            expires_in = max(0, int(remaining.total_seconds()))
            
            return {
                'user_id': token_record.user_id.id,
                'username': token_record.user_id.login,
                'expires_at': token_record[expiry_field].isoformat() if token_record[expiry_field] else None,
                'expires_in': expires_in,
                'is_expired': expires_in <= 0
            }
        
        return None

class Authentication(http.Controller, AuthMixin):

    @route(f'{BASE_URL}/login', type='http', cors="*", csrf=False, auth='none', methods=['POST'])
    def login(self, **kw):
        """
        Login and generate tokens.
        """
        try:
            # Parse JSON data from request body
            try:
                if request.httprequest.data:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    data = dict(request.httprequest.form)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return Response(json.dumps({
                    "status": False,
                    "message": "Invalid JSON format",
                    "error": str(e)
                }), status=400, content_type='application/json')
            
            # Validate required fields
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return Response(json.dumps({
                    "status": False,
                    "message": "Missing required fields",
                    "error": "Username and password are required"
                }), status=400, content_type='application/json')
            
            # Authenticate the user
            user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
            if not user:
                return Response(json.dumps({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid username or password"
                }), status=401, content_type='application/json')
            
            # Verify password using Odoo's authentication system
            # We need to get db name from request.session.db or from config
            db = request.session.db
            credential = {'login': username, 'password': password, 'type': 'password'}
            
            try:
                uid = request.session.authenticate(db, credential)
                if not uid:
                    return Response(json.dumps({
                        "status": False,
                        "message": "Authentication failed",
                        "error": "Invalid username or password"
                    }), status=401, content_type='application/json')
            except Exception as auth_error:
                return Response(json.dumps({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid credentials"
                }), status=401, content_type='application/json')
            
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

            if request.env.user.has_group("base.group_system"):
                role = "ADMIN"
            elif request.env.user.has_group("e_menu.group_merchant"):
                role = "MERCHANT"
            else:
                role = "NORMAL"
            
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
                    'roles': role
                }
            }
            
            return Response(json.dumps(response_data), status=200, content_type='application/json')
            
        except Exception as e:
            _logger.error(f"Login error: {str(e)}")
            return Response(json.dumps({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during login"
            }), status=500, content_type='application/json')

    @route(f'{BASE_URL}/refresh', type='http', cors="*", csrf=False, auth='none', methods=['POST'])
    def refresh_token(self, **kwargs):
        """
        Generate a new access token using a valid refresh token.
        """
        try:
            # Check Content-Type header
            content_type = request.httprequest.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                return Response(json.dumps({
                    "status": False,
                    "message": "Invalid request format",
                    "error": "Content-Type must be application/json"
                }), status=400, content_type='application/json')
            
            try:
                if request.httprequest.data:
                    request_data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    request_data = dict(request.httprequest.form)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return Response(json.dumps({
                    "status": False,
                    "message": "Invalid JSON format",
                    "error": str(e)
                }), status=400, content_type='application/json')
            
            refresh_token = request_data.get('refresh_token')
            if not refresh_token:
                return Response(json.dumps({
                    "status": False,
                    "message": "Missing required field",
                    "error": "Refresh token is required"
                }), status=400, content_type='application/json')
            
            # Validate the refresh token using token model directly or helper
            token_model = request.env['res.user.token'].sudo()
            user_id = token_model.validate_token(refresh_token, token_type='refresh')

            if not user_id:
                return Response(json.dumps({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid or expired refresh token"
                }), status=401, content_type='application/json')

            # Generate a new access token
            new_access_token = self._generate_token(user_id, 'access', minutes=30)

            # Update the database with the new token
            token_model.create_token(
                user_id=user_id,
                access_token=new_access_token,
                refresh_token=refresh_token,
                access_expiry=datetime.utcnow() + timedelta(minutes=30),
                refresh_expiry=datetime.utcnow() + timedelta(days=7)
            )

            response_data = {
                "status": True,
                "message": "Token refreshed successfully",
                "data": {
                    "access_token": new_access_token,
                    "token_type": "Bearer",
                    "expires_in": 1800
                }
            }

            return Response(json.dumps(response_data), status=200, content_type='application/json')
            
        except Exception as e:
            _logger.error(f"Token refresh error: {str(e)}")
            return Response(json.dumps({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during token refresh"
            }), status=500, content_type='application/json')

    @route(f'{BASE_URL}/logout', auth="angkit", type="http", methods=["POST"], csrf=False, cors="*")
    def logout(self, **kwargs):
        """
        Logout a user by invalidating their access token.
        """
        try:
            access_token_header = request.httprequest.headers.get('Authorization')
            if not access_token_header:
                return Response(json.dumps({
                    "status": False,
                    "message": "Access token missing",
                    "error": "Authorization header is required"
                }), status=400, content_type='application/json')

            if access_token_header.startswith('Bearer '):
                access_token_header = access_token_header[7:]

            token_model = request.env['res.user.token'].sudo()
            token = token_model.search([('access_token', '=', hashlib.sha256(access_token_header.encode()).hexdigest())], limit=1)

            if token:
                token.write({'active': False})
                request.session.logout(keep_db=True)
                return Response(json.dumps({
                    "status": True,
                    "message": "Successfully logged out"
                }), status=200, content_type='application/json')

            return Response(json.dumps({
                "status": False,
                "message": "Authentication failed",
                "error": "Invalid access token"
            }), status=401, content_type='application/json')
            
        except Exception as e:
            _logger.error(f"Logout error: {str(e)}")
            return Response(json.dumps({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during logout"
            }), status=500, content_type='application/json')
