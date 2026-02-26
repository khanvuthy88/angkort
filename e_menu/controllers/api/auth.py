from odoo import fields, http
from odoo.http import request, route
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

    @route(f'{BASE_URL}/<path:path>', type='http', auth='none', methods=['OPTIONS'], csrf=False, cors="*")
    def api_options(self, path=None, **kw):
        """
        Global handler for CORS preflight (OPTIONS) requests.
        Returns a 200 OK with the necessary Access-Control headers.
        """
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization',
            'Access-Control-Max-Age': '86400',
        }
        return request.make_response('', headers=headers)

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
                return request.make_json_response({
                    "status": False,
                    "message": "Invalid JSON format",
                    "error": str(e)
                }, status=400)

            # Validate required fields
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return request.make_json_response({
                    "status": False,
                    "message": "Missing required fields",
                    "error": "Username and password are required"
                }, status=400)

            # Authenticate the user
            user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
            if not user:
                return request.make_json_response({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid username or password"
                }, status=401)

            # Verify password using Odoo's authentication system
            # We need to get db name from request.session.db or from config
            db = request.session.db
            credential = {'login': username, 'password': password, 'type': 'password'}

            try:
                uid = request.session.authenticate(db, credential)
                if not uid:
                    return request.make_json_response({
                        "status": False,
                        "message": "Authentication failed",
                        "error": "Invalid username or password"
                    }, status=401)
            except Exception as auth_error:
                return request.make_json_response({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid credentials"
                }, status=401)

            # Generate tokens
            access_token = self._generate_token(user.id, 'access', minutes=30)
            refresh_token = self._generate_token(user.id, 'refresh', days=7)

            # Deactivate any existing tokens for this user, then store new ones
            token_model = request.env['res.user.token'].sudo()
            self._revoke_all_user_tokens(user.id)
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

            # Shops owned by the current user (created by this user)
            shops = request.env['res.partner'].sudo().search([
                ('type', '=', 'store'),
                ('create_uid', '=', user.id)
            ], order='id')
            shops_data = [{
                'id': shop.id,
                'name': shop.name or '',
                'phone': shop.phone or '',
                'customer_address': shop.customer_address or '',
            } for shop in shops]
            
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
                    "roles": role,
                    "shops": shops_data
                }
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            return request.make_json_response(response_data, status=200, headers=headers)

        except Exception as e:
            _logger.error(f"Login error: {str(e)}")
            return request.make_json_response({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during login"
            }, status=500)

    @route(f'{BASE_URL}/register', type='http', cors="*", csrf=False, auth='public', methods=['POST'])
    def register(self, **kw):
        """
        Register a new user and generate tokens.
        """
        try:
            # Parse JSON data from request body
            try:
                if request.httprequest.data:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    data = dict(request.httprequest.form)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return request.make_json_response({
                    "status": False,
                    "message": "Invalid JSON format",
                    "error": str(e)
                }, status=400)

            # Validate required fields
            name = data.get('name')
            username = data.get('username')
            password = data.get('password')

            if not name or not username or not password:
                return request.make_json_response({
                    "status": False,
                    "message": "Missing required fields",
                    "error": "Name, username, and password are required"
                }, status=400)

            # Check if user already exists
            # Use active_test=False to find inactive users too, preventing "User already exists" constraint error
            User = request.env['res.users'].sudo().with_context(active_test=False)
            existing_user = User.search([('login', '=', username)], limit=1)
            if existing_user:
                return request.make_json_response({
                    "status": False,
                    "message": "Registration failed",
                    "error": "Username already exists"
                }, status=409)
            
            # Create the new user
            try:
                # 1. Fetch the template user ID from system parameters
                template_user_id = request.env['ir.config_parameter'].sudo().get_param('auth_signup.template_user_id')
                
                # 2. Get the template user record with sudo permissions
                if template_user_id:
                    template_user = request.env['res.users'].sudo().browse(int(template_user_id))
                else:
                    template_user = request.env['res.users'].sudo()
                
                # Prepare values for user creation
                values = {
                    'name': name,
                    'login': username,
                    'password': password,
                    'active': True,
                }
                
                # 3. Create the user by copying the template or standard create
                # We use with_context(no_reset_password=True) to prevent sending emails immediately
                if template_user.exists():
                    # Explicitly copy from the configured template
                    user = template_user.with_context(no_reset_password=True).copy(values)
                else:
                    # Fallback to standard create if no template configured
                    # Add Internal User group by default in this case
                    values['groups_id'] = [(4, request.env.ref('base.group_user').id)]
                    user = request.env['res.users'].with_context(no_reset_password=True).sudo().create(values)
                
                # Check for singleton explicitly to be safe
                user.ensure_one()
                    
            except Exception as e:
                # Log the full error for server-side debugging if needed
                _logger.exception("Registration failed during user creation")
                return request.make_json_response({
                    "status": False,
                    "message": "Registration failed",
                    "error": f"Could not create user: {str(e)}"
                }, status=500)
            
            # Generate tokens
            access_token = self._generate_token(user.id, 'access', minutes=30)
            refresh_token = self._generate_token(user.id, 'refresh', days=7)
            
            # Deactivate any existing tokens for this user, then store new ones
            token_model = request.env['res.user.token'].sudo()
            self._revoke_all_user_tokens(user.id)
            token_model.create_token(
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                access_expiry=datetime.utcnow() + timedelta(minutes=30),
                refresh_expiry=datetime.utcnow() + timedelta(days=7)
            )

            # Determine role (default to NORMAL for new registrations via this route)
            role = "NORMAL"
            
            # Prepare success response
            response_data = {
                "status": True,
                "message": "Registration successful",
                "data": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 1800,
                    "user_id": user.id,
                    "username": user.login,
                    "name": user.name,
                    "email": user.email,
                    'roles': role
                }
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            return request.make_json_response(response_data, status=201, headers=headers)

        except Exception as e:
            _logger.error(f"Registration error: {str(e)}")
            return request.make_json_response({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during registration"
            }, status=500)

    @route(f'{BASE_URL}/refresh', type='http', cors="*", csrf=False, auth='none', methods=['POST'])
    def refresh_token(self, **kwargs):
        """
        Generate a new access token using a valid refresh token.
        """
        try:
            # Check Content-Type header
            content_type = request.httprequest.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                return request.make_json_response({
                    "status": False,
                    "message": "Invalid request format",
                    "error": "Content-Type must be application/json"
                }, status=400)

            try:
                if request.httprequest.data:
                    request_data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    request_data = dict(request.httprequest.form)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return request.make_json_response({
                    "status": False,
                    "message": "Invalid JSON format",
                    "error": str(e)
                }, status=400)

            refresh_token = request_data.get('refresh_token')
            if not refresh_token:
                return request.make_json_response({
                    "status": False,
                    "message": "Missing required field",
                    "error": "Refresh token is required"
                }, status=400)

            # Validate the refresh token and rotate the access token in-place
            token_model = request.env['res.user.token'].sudo()

            # First peek at user_id so we can generate a token with it
            user_id = token_model.validate_token(refresh_token, token_type='refresh')
            if not user_id:
                return request.make_json_response({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid or expired refresh token"
                }, status=401)

            # Generate a new access token
            new_access_token = self._generate_token(user_id, 'access', minutes=30)

            # Update the existing record instead of creating a duplicate
            rotated_user_id = token_model.refresh_access_token(
                refresh_token=refresh_token,
                new_access_token=new_access_token,
                access_expiry=datetime.utcnow() + timedelta(minutes=30),
            )
            if not rotated_user_id:
                return request.make_json_response({
                    "status": False,
                    "message": "Authentication failed",
                    "error": "Invalid or expired refresh token"
                }, status=401)

            response_data = {
                "status": True,
                "message": "Token refreshed successfully",
                "data": {
                    "access_token": new_access_token,
                    "token_type": "Bearer",
                    "expires_in": 1800
                }
            }

            return request.make_json_response(response_data, status=200)

        except Exception as e:
            _logger.error(f"Token refresh error: {str(e)}")
            return request.make_json_response({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during token refresh"
            }, status=500)

    @route(f'{BASE_URL}/logout', auth="angkit", type="http", methods=["POST"], csrf=False, cors="*")
    def logout(self, **kwargs):
        """
        Logout a user by invalidating their access token.
        """
        try:
            access_token_header = request.httprequest.headers.get('Authorization')
            if not access_token_header:
                return request.make_json_response({
                    "status": False,
                    "message": "Access token missing",
                    "error": "Authorization header is required"
                }, status=400)

            if access_token_header.startswith('Bearer '):
                access_token_header = access_token_header[7:]

            token_model = request.env['res.user.token'].sudo()
            token = token_model.search([('access_token', '=', hashlib.sha256(access_token_header.encode()).hexdigest())], limit=1)

            if token:
                token.write({'active': False})
                request.session.logout(keep_db=True)
                return request.make_json_response({
                    "status": True,
                    "message": "Successfully logged out"
                }, status=200)

            return request.make_json_response({
                "status": False,
                "message": "Authentication failed",
                "error": "Invalid access token"
            }, status=401)

        except Exception as e:
            _logger.error(f"Logout error: {str(e)}")
            return request.make_json_response({
                "status": False,
                "message": "Internal server error",
                "error": "An unexpected error occurred during logout"
            }, status=500)



