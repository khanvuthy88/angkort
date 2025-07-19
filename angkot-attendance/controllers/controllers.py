# -*- coding: utf-8 -*-
import json
import logging
import jwt
import hashlib
import secrets
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessError, UserError
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized
from functools import wraps

_logger = logging.getLogger(__name__)


def require_auth(f):
    """Decorator to require JWT authentication for API endpoints"""
    @wraps(f)
    def decorated_function(self, *args, **kwargs):
        try:
            # Authenticate request
            payload = self._authenticate_request()
            # Store user info in request for later use
            request.auth_user = self._get_current_user()
            request.auth_payload = payload
            return f(self, *args, **kwargs)
        except Exception as e:
            return self._handle_error(e)
    return decorated_function


def optional_auth(f):
    """Decorator for optional JWT authentication - doesn't fail if no auth provided"""
    @wraps(f)
    def decorated_function(self, *args, **kwargs):
        try:
            # Try to authenticate, but don't fail if no auth provided
            auth_header = request.httprequest.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                try:
                    token = auth_header.split(' ')[1]
                    payload = TokenManager.verify_token(token, 'access')
                    request.auth_user = self._get_current_user()
                    request.auth_payload = payload
                except Exception:
                    # Authentication failed, but we continue without auth
                    request.auth_user = None
                    request.auth_payload = None
            else:
                request.auth_user = None
                request.auth_payload = None
            
            return f(self, *args, **kwargs)
        except Exception as e:
            return self._handle_error(e)
    return decorated_function


def require_json(f):
    """Decorator to require JSON request body"""
    @wraps(f)
    def decorated_function(self, *args, **kwargs):
        try:
            # Parse JSON data
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except json.JSONDecodeError:
                raise AttendanceValidationError("Invalid JSON data")
            
            # Store parsed data in request
            request.json_data = data
            return f(self, *args, **kwargs)
        except Exception as e:
            return self._handle_error(e)
    return decorated_function


def require_role(role_name):
    """Decorator to require specific user role/group"""
    def decorator(f):
        @wraps(f)
        def decorated_function(self, *args, **kwargs):
            try:
                # First authenticate
                payload = self._authenticate_request()
                user = self._get_current_user()
                
                # Check if user has the required role
                if not user.has_group(role_name):
                    return Response(
                        json.dumps({'error': f'Access denied. Required role: {role_name}', 'type': 'authorization_error'}),
                        status=403,
                        content_type='application/json'
                    )
                
                # Store user info in request for later use
                request.auth_user = user
                request.auth_payload = payload
                return f(self, *args, **kwargs)
            except Exception as e:
                return self._handle_error(e)
        return decorated_function
    return decorator


class AttendanceValidationError(Exception):
    """Custom exception for attendance validation errors"""
    pass


class AttendanceAPIError(Exception):
    """Custom exception for attendance API errors"""
    pass


class TokenManager:
    """JWT Token management for authentication"""
    
    # JWT Configuration
    JWT_SECRET_KEY = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRY = timedelta(hours=1)  # 1 hour
    REFRESH_TOKEN_EXPIRY = timedelta(days=30)  # 30 days
    
    @classmethod
    def generate_tokens(cls, user_id: int, employee_id: Optional[int] = None) -> Dict[str, str]:
        """Generate access and refresh tokens"""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'employee_id': employee_id,
            'type': 'access',
            'iat': now,
            'exp': now + cls.ACCESS_TOKEN_EXPIRY
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'employee_id': employee_id,
            'type': 'refresh',
            'iat': now,
            'exp': now + cls.REFRESH_TOKEN_EXPIRY,
            'jti': secrets.token_urlsafe(32)  # JWT ID for refresh token
        }
        
        # Generate tokens
        access_token = jwt.encode(access_payload, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
        
        # Store refresh token in database for revocation
        cls._store_refresh_token(refresh_payload['jti'], user_id, refresh_payload['exp'])
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(cls.ACCESS_TOKEN_EXPIRY.total_seconds())
        }
    
    @classmethod
    def verify_token(cls, token: str, token_type: str = 'access') -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, cls.JWT_SECRET_KEY, algorithms=[cls.JWT_ALGORITHM])
            
            # Check token type
            if payload.get('type') != token_type:
                raise jwt.InvalidTokenError("Invalid token type")
            
            # For refresh tokens, check if they're revoked
            if token_type == 'refresh':
                if not cls._is_refresh_token_valid(payload.get('jti')):
                    raise jwt.InvalidTokenError("Refresh token has been revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
    
    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Dict[str, str]:
        """Generate new access token using refresh token"""
        try:
            # Verify refresh token
            payload = cls.verify_token(refresh_token, 'refresh')
            
            # Generate new access token
            now = datetime.utcnow()
            access_payload = {
                'user_id': payload['user_id'],
                'employee_id': payload.get('employee_id'),
                'type': 'access',
                'iat': now,
                'exp': now + cls.ACCESS_TOKEN_EXPIRY
            }
            
            access_token = jwt.encode(access_payload, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
            
            return {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': int(cls.ACCESS_TOKEN_EXPIRY.total_seconds())
            }
            
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid refresh token: {str(e)}")
    
    @classmethod
    def revoke_refresh_token(cls, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        try:
            payload = cls.verify_token(refresh_token, 'refresh')
            jti = payload.get('jti')
            if jti:
                return cls._revoke_refresh_token(jti)
            return False
        except jwt.InvalidTokenError:
            return False
    
    @classmethod
    def _store_refresh_token(cls, jti: str, user_id: int, expires_at: datetime) -> None:
        """Store refresh token in database"""
        try:
            # Store in ir.config_parameter for simplicity
            # In production, use a dedicated table for refresh tokens
            token_data = {
                'jti': jti,
                'user_id': user_id,
                'expires_at': expires_at.isoformat(),
                'revoked': False
            }
            
            param_name = f'attendance_refresh_token_{jti}'
            request.env['ir.config_parameter'].sudo().set_param(
                param_name, 
                json.dumps(token_data)
            )
        except Exception as e:
            _logger.error(f"Failed to store refresh token: {e}")
    
    @classmethod
    def _is_refresh_token_valid(cls, jti: str) -> bool:
        """Check if refresh token is valid and not revoked"""
        try:
            param_name = f'attendance_refresh_token_{jti}'
            token_data_str = request.env['ir.config_parameter'].sudo().get_param(param_name)
            
            if not token_data_str:
                return False
            
            token_data = json.loads(token_data_str)
            
            # Check if revoked
            if token_data.get('revoked', False):
                return False
            
            # Check if expired
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            if datetime.utcnow() > expires_at:
                return False
            
            return True
            
        except Exception as e:
            _logger.error(f"Failed to check refresh token validity: {e}")
            return False
    
    @classmethod
    def _revoke_refresh_token(cls, jti: str) -> bool:
        """Revoke a refresh token"""
        try:
            param_name = f'attendance_refresh_token_{jti}'
            token_data_str = request.env['ir.config_parameter'].sudo().get_param(param_name)
            
            if token_data_str:
                token_data = json.loads(token_data_str)
                token_data['revoked'] = True
                request.env['ir.config_parameter'].sudo().set_param(
                    param_name, 
                    json.dumps(token_data)
                )
                return True
            
            return False
            
        except Exception as e:
            _logger.error(f"Failed to revoke refresh token: {e}")
            return False


class AttendanceValidator:
    """Pydantic-like validation for attendance data"""
    
    @staticmethod
    def validate_attendance_create(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate attendance creation data"""
        required_fields = ['employee_id']
        optional_fields = ['check_in', 'check_out', 'date', 'status']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                raise AttendanceValidationError(f"Missing required field: {field}")
        
        # Validate employee_id
        if not isinstance(data['employee_id'], int) or data['employee_id'] <= 0:
            raise AttendanceValidationError("employee_id must be a positive integer")
        
        # Validate check_in
        if 'check_in' in data and data['check_in']:
            try:
                if isinstance(data['check_in'], str):
                    data['check_in'] = datetime.fromisoformat(data['check_in'].replace('Z', '+00:00'))
                elif not isinstance(data['check_in'], datetime):
                    raise AttendanceValidationError("check_in must be a valid datetime")
            except ValueError:
                raise AttendanceValidationError("Invalid check_in datetime format")
        
        # Validate check_out
        if 'check_out' in data and data['check_out']:
            try:
                if isinstance(data['check_out'], str):
                    data['check_out'] = datetime.fromisoformat(data['check_out'].replace('Z', '+00:00'))
                elif not isinstance(data['check_out'], datetime):
                    raise AttendanceValidationError("check_out must be a valid datetime")
            except ValueError:
                raise AttendanceValidationError("Invalid check_out datetime format")
        
        # Validate date
        if 'date' in data and data['date']:
            try:
                if isinstance(data['date'], str):
                    data['date'] = datetime.strptime(data['date'], '%Y-%m-%d').date()
                elif not isinstance(data['date'], date):
                    raise AttendanceValidationError("date must be a valid date")
            except ValueError:
                raise AttendanceValidationError("Invalid date format. Use YYYY-MM-DD")
        
        # Validate status
        if 'status' in data and data['status']:
            valid_statuses = ['present', 'absent', 'late', 'on_time', 'early_departure']
            if data['status'] not in valid_statuses:
                raise AttendanceValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        
        return data
    
    @staticmethod
    def validate_attendance_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate attendance update data"""
        valid_fields = ['employee_id', 'check_in', 'check_out', 'date', 'status']
        
        # Check if at least one field is provided
        if not any(field in data for field in valid_fields):
            raise AttendanceValidationError("At least one field must be provided for update")
        
        return AttendanceValidator.validate_attendance_create(data)
    
    @staticmethod
    def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate query filters"""
        valid_filters = ['employee_id', 'date_from', 'date_to', 'status', 'limit', 'offset']
        
        validated_filters = {}
        for key, value in filters.items():
            if key not in valid_filters:
                continue
            
            if key == 'employee_id':
                if not isinstance(value, int) or value <= 0:
                    raise AttendanceValidationError("employee_id filter must be a positive integer")
                validated_filters[key] = value
            
            elif key in ['date_from', 'date_to']:
                try:
                    if isinstance(value, str):
                        validated_filters[key] = datetime.strptime(value, '%Y-%m-%d').date()
                    elif isinstance(value, date):
                        validated_filters[key] = value
                    else:
                        raise AttendanceValidationError(f"{key} must be a valid date")
                except ValueError:
                    raise AttendanceValidationError(f"Invalid {key} date format. Use YYYY-MM-DD")
            
            elif key == 'status':
                valid_statuses = ['present', 'absent', 'late', 'on_time', 'early_departure']
                if value not in valid_statuses:
                    raise AttendanceValidationError(f"Invalid status filter. Must be one of: {valid_statuses}")
                validated_filters[key] = value
            
            elif key in ['limit', 'offset']:
                if not isinstance(value, int) or value < 0:
                    raise AttendanceValidationError(f"{key} must be a non-negative integer")
                validated_filters[key] = value
        
        return validated_filters
    
    @staticmethod
    def validate_login_credentials(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate login credentials"""
        required_fields = ['username', 'password']
        
        for field in required_fields:
            if field not in data:
                raise AttendanceValidationError(f"Missing required field: {field}")
        
        if not isinstance(data['username'], str) or not data['username'].strip():
            raise AttendanceValidationError("Username cannot be empty")
        
        if not isinstance(data['password'], str) or not data['password'].strip():
            raise AttendanceValidationError("Password cannot be empty")
        
        return data


class AttendanceSerializer:
    """Serializer for attendance data"""
    
    @staticmethod
    def serialize_attendance(attendance) -> Dict[str, Any]:
        """Serialize a single attendance record"""
        return {
            'id': attendance.id,
            'employee_id': attendance.employee_id.id,
            'employee_name': attendance.employee_id.name,
            'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
            'check_out': attendance.check_out.isoformat() if attendance.check_out else None,
            'date': attendance.check_in.date().isoformat() if attendance.check_in else None,
            'worked_hours': attendance.worked_hours,
            'status': AttendanceSerializer._determine_status(attendance),
            'department_id': attendance.department_id.id if attendance.department_id else None,
            'department_name': attendance.department_id.name if attendance.department_id else None,
            'created_at': attendance.create_date.isoformat() if attendance.create_date else None,
            'updated_at': attendance.write_date.isoformat() if attendance.write_date else None,
        }
    
    @staticmethod
    def serialize_attendance_list(attendances, total_count: int = None, limit: int = None, offset: int = None) -> Dict[str, Any]:
        """Serialize a list of attendance records with pagination info"""
        data = {
            'attendances': [AttendanceSerializer.serialize_attendance(att) for att in attendances],
            'total_count': total_count or len(attendances),
        }
        
        if limit is not None:
            data['limit'] = limit
        if offset is not None:
            data['offset'] = offset
        
        return data
    
    @staticmethod
    def _determine_status(attendance) -> str:
        """Determine attendance status based on check-in/check-out times"""
        if not attendance.check_in:
            return 'absent'
        
        if not attendance.check_out:
            return 'present'
        
        # Calculate if late based on check-in time (assuming 9 AM as standard start time)
        check_in_time = attendance.check_in.time()
        if check_in_time > datetime.strptime('09:00:00', '%H:%M:%S').time():
            return 'late'
        
        # Calculate if early departure (assuming 5 PM as standard end time)
        check_out_time = attendance.check_out.time()
        if check_out_time < datetime.strptime('17:00:00', '%H:%M:%S').time():
            return 'early_departure'
        
        return 'on_time'


class AttendanceService:
    """Service layer for attendance operations"""
    
    @staticmethod
    def create_attendance(data: Dict[str, Any]) -> Any:
        """Create a new attendance record"""
        try:
            # Set default values
            if 'check_in' not in data or not data['check_in']:
                data['check_in'] = datetime.now()
            
            if 'date' not in data or not data['date']:
                data['date'] = data['check_in'].date()
            
            # Create attendance record
            attendance = request.env['hr.attendance'].create({
                'employee_id': data['employee_id'],
                'check_in': data['check_in'],
                'check_out': data.get('check_out'),
            })
            
            return attendance
            
        except Exception as e:
            _logger.error(f"Error creating attendance: {str(e)}")
            raise AttendanceAPIError(f"Failed to create attendance: {str(e)}")
    
    @staticmethod
    def get_attendance(attendance_id: int) -> Any:
        """Get a specific attendance record by ID"""
        try:
            attendance = request.env['hr.attendance'].browse(attendance_id)
            if not attendance.exists():
                raise NotFound(f"Attendance record with ID {attendance_id} not found")
            return attendance
        except NotFound:
            raise
        except Exception as e:
            _logger.error(f"Error retrieving attendance {attendance_id}: {str(e)}")
            raise AttendanceAPIError(f"Failed to retrieve attendance: {str(e)}")
    
    @staticmethod
    def get_attendances(filters: Dict[str, Any] = None) -> tuple:
        """Get attendance records with optional filters"""
        try:
            domain = []
            
            if filters:
                if 'employee_id' in filters:
                    domain.append(('employee_id', '=', filters['employee_id']))
                
                if 'date_from' in filters:
                    domain.append(('check_in', '>=', datetime.combine(filters['date_from'], datetime.min.time())))
                
                if 'date_to' in filters:
                    domain.append(('check_in', '<=', datetime.combine(filters['date_to'], datetime.max.time())))
                
                if 'status' in filters:
                    # Status filtering logic would need to be implemented based on business rules
                    pass
            
            # Get total count
            total_count = request.env['hr.attendance'].search_count(domain)
            
            # Apply pagination
            limit = filters.get('limit', 50) if filters else 50
            offset = filters.get('offset', 0) if filters else 0
            
            attendances = request.env['hr.attendance'].search(
                domain,
                limit=limit,
                offset=offset,
                order='check_in desc'
            )
            
            return attendances, total_count, limit, offset
            
        except Exception as e:
            _logger.error(f"Error retrieving attendances: {str(e)}")
            raise AttendanceAPIError(f"Failed to retrieve attendances: {str(e)}")
    
    @staticmethod
    def update_attendance(attendance_id: int, data: Dict[str, Any]) -> Any:
        """Update an existing attendance record"""
        try:
            attendance = AttendanceService.get_attendance(attendance_id)
            
            update_data = {}
            if 'employee_id' in data:
                update_data['employee_id'] = data['employee_id']
            if 'check_in' in data:
                update_data['check_in'] = data['check_in']
            if 'check_out' in data:
                update_data['check_out'] = data['check_out']
            
            attendance.write(update_data)
            return attendance
            
        except NotFound:
            raise
        except Exception as e:
            _logger.error(f"Error updating attendance {attendance_id}: {str(e)}")
            raise AttendanceAPIError(f"Failed to update attendance: {str(e)}")
    
    @staticmethod
    def delete_attendance(attendance_id: int) -> bool:
        """Delete an attendance record"""
        try:
            attendance = AttendanceService.get_attendance(attendance_id)
            attendance.unlink()
            return True
        except NotFound:
            raise
        except Exception as e:
            _logger.error(f"Error deleting attendance {attendance_id}: {str(e)}")
            raise AttendanceAPIError(f"Failed to delete attendance: {str(e)}")
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user info"""
        try:
            # Authenticate user using Odoo's authentication system
            uid = request.env['res.users'].sudo().authenticate(
                request.db, username, password, {'interactive': False}
            )
            
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                employee = user.employee_id
                
                return {
                    'user_id': uid,
                    'username': user.login,
                    'name': user.name,
                    'employee_id': employee.id if employee else None,
                    'employee_name': employee.name if employee else None,
                    'email': user.email,
                    'groups': [group.name for group in user.groups_id]
                }
            
            return None
            
        except Exception as e:
            _logger.error(f"Authentication error: {str(e)}")
            return None


class AttendanceController(http.Controller):
    """RESTful API controller for attendance management with JWT authentication"""
    
    def _handle_error(self, error: Exception) -> Response:
        """Handle different types of errors and return appropriate HTTP responses"""
        if isinstance(error, AttendanceValidationError):
            return Response(
                json.dumps({'error': str(error), 'type': 'validation_error'}),
                status=400,
                content_type='application/json'
            )
        elif isinstance(error, jwt.InvalidTokenError):
            return Response(
                json.dumps({'error': str(error), 'type': 'authentication_error'}),
                status=401,
                content_type='application/json'
            )
        elif isinstance(error, NotFound):
            return Response(
                json.dumps({'error': str(error), 'type': 'not_found'}),
                status=404,
                content_type='application/json'
            )
        elif isinstance(error, Unauthorized):
            return Response(
                json.dumps({'error': str(error), 'type': 'unauthorized'}),
                status=401,
                content_type='application/json'
            )
        elif isinstance(error, AttendanceAPIError):
            return Response(
                json.dumps({'error': str(error), 'type': 'api_error'}),
                status=500,
                content_type='application/json'
            )
        else:
            _logger.error(f"Unexpected error: {str(error)}")
            return Response(
                json.dumps({'error': 'Internal server error', 'type': 'internal_error'}),
                status=500,
                content_type='application/json'
            )
    
    def _authenticate_request(self) -> Dict[str, Any]:
        """Authenticate request using Bearer token"""
        auth_header = request.httprequest.headers.get('Authorization')
        
        if not auth_header:
            raise Unauthorized("Missing Authorization header")
        
        if not auth_header.startswith('Bearer '):
            raise Unauthorized("Invalid Authorization header format. Use 'Bearer <token>'")
        
        token = auth_header.split(' ')[1]
        
        try:
            # Verify and decode the token
            payload = TokenManager.verify_token(token, 'access')
            return payload
        except jwt.InvalidTokenError as e:
            raise Unauthorized(f"Invalid token: {str(e)}")
    
    def _get_current_user(self) -> Any:
        """Get current user from token"""
        payload = self._authenticate_request()
        user_id = payload.get('user_id')
        
        if not user_id:
            raise Unauthorized("Invalid token payload")
        
        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            raise Unauthorized("User not found")
        
        return user
    



    @http.route('/api/v1/auth/login', type='http', methods=['POST'], auth='public', csrf=False)
    def login(self, **kwargs):
        """User login endpoint"""
        try:
            # JSON parsing is handled by decorator
            data = request.json_data
            
            # Validate credentials
            validated_data = AttendanceValidator.validate_login_credentials(data)
            
            # Authenticate user
            user_info = AttendanceService.authenticate_user(
                validated_data['username'], 
                validated_data['password']
            )
            
            if not user_info:
                return Response(
                    json.dumps({'error': 'Invalid credentials', 'type': 'authentication_error'}),
                    status=401,
                    content_type='application/json'
                )
            
            # Generate tokens
            tokens = TokenManager.generate_tokens(
                user_info['user_id'], 
                user_info.get('employee_id')
            )
            
            # Return response
            response_data = {
                'user': user_info,
                'tokens': tokens
            }
            
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_json
    @http.route('/api/v1/auth/refresh', type='http', methods=['POST'], auth='public', csrf=False)
    def refresh_token(self, **kwargs):
        """Refresh access token endpoint"""
        try:
            # JSON parsing is handled by decorator
            data = request.json_data
            
            if 'refresh_token' not in data:
                raise AttendanceValidationError("Missing refresh_token")
            
            # Refresh the access token
            new_tokens = TokenManager.refresh_access_token(data['refresh_token'])
            
            return Response(
                json.dumps(new_tokens),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_json
    @http.route('/api/v1/auth/logout', type='http', methods=['POST'], auth='public', csrf=False)
    def logout(self, **kwargs):
        """User logout endpoint"""
        try:
            # JSON parsing is handled by decorator
            data = request.json_data
            
            if 'refresh_token' not in data:
                raise AttendanceValidationError("Missing refresh_token")
            
            # Revoke the refresh token
            success = TokenManager.revoke_refresh_token(data['refresh_token'])
            
            if success:
                return Response(
                    json.dumps({'message': 'Successfully logged out'}),
                    status=200,
                    content_type='application/json'
                )
            else:
                return Response(
                    json.dumps({'error': 'Invalid refresh token', 'type': 'authentication_error'}),
                    status=400,
                    content_type='application/json'
                )
            
        except Exception as e:
            return self._handle_error(e)
    
    @http.route('/api/v1/auth/me', type='http', methods=['GET'], auth='public', csrf=False)
    def get_current_user(self, **kwargs):
        """Get current user information"""
        try:
            # Authenticate request
            payload = self._authenticate_request()
            user = self._get_current_user()
            
            # Get user info
            employee = user.employee_id
            user_info = {
                'user_id': user.id,
                'username': user.login,
                'name': user.name,
                'employee_id': employee.id if employee else None,
                'employee_name': employee.name if employee else None,
                'email': user.email,
                'groups': [group.name for group in user.groups_id]
            }
            
            return Response(
                json.dumps(user_info),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_auth
    @require_json
    @http.route('/api/v1/attendance', type='http', methods=['POST'], auth='public', csrf=False)
    def create_attendance(self, **kwargs):
        """Create a new attendance record"""
        try:
            # Authentication and JSON parsing are handled by decorators
            data = request.json_data
            
            # Validate data
            validated_data = AttendanceValidator.validate_attendance_create(data)
            
            # Create attendance
            attendance = AttendanceService.create_attendance(validated_data)
            
            # Return response
            response_data = AttendanceSerializer.serialize_attendance(attendance)
            return Response(
                json.dumps(response_data),
                status=201,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_auth
    @http.route('/api/v1/attendance', type='http', methods=['GET'], auth='public', csrf=False)
    def list_attendances(self, **kwargs):
        """Retrieve a list of attendance records with optional filters"""
        try:
            # Parse filters from query parameters
            filters = {}
            for key, value in kwargs.items():
                if key in ['employee_id', 'limit', 'offset']:
                    try:
                        filters[key] = int(value)
                    except ValueError:
                        raise AttendanceValidationError(f"Invalid {key} value: must be an integer")
                elif key in ['date_from', 'date_to', 'status']:
                    filters[key] = value
            
            # Validate filters
            validated_filters = AttendanceValidator.validate_filters(filters)
            
            # Get attendances
            attendances, total_count, limit, offset = AttendanceService.get_attendances(validated_filters)
            
            # Return response
            response_data = AttendanceSerializer.serialize_attendance_list(
                attendances, total_count, limit, offset
            )
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_auth
    @http.route('/api/v1/attendance/<int:attendance_id>', type='http', methods=['GET'], auth='public', csrf=False)
    def get_attendance(self, attendance_id, **kwargs):
        """Retrieve a specific attendance record by ID"""
        try:
            # Authentication and JSON parsing are handled by decorators
            # Get attendance
            attendance = AttendanceService.get_attendance(attendance_id)
            
            # Return response
            response_data = AttendanceSerializer.serialize_attendance(attendance)
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_auth
    @require_json
    @http.route('/api/v1/attendance/<int:attendance_id>', type='http', methods=['PUT'], auth='public', csrf=False)
    def update_attendance(self, attendance_id, **kwargs):
        """Update an existing attendance record"""
        try:
            # Authentication and JSON parsing are handled by decorators
            data = request.json_data
            
            # Validate data
            validated_data = AttendanceValidator.validate_attendance_update(data)
            
            # Update attendance
            attendance = AttendanceService.update_attendance(attendance_id, validated_data)
            
            # Return response
            response_data = AttendanceSerializer.serialize_attendance(attendance)
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @require_auth
    @http.route('/api/v1/attendance/<int:attendance_id>', type='http', methods=['DELETE'], auth='public', csrf=False)
    def delete_attendance(self, attendance_id, **kwargs):
        """Delete an attendance record"""
        try:
            # Authentication and JSON parsing are handled by decorators
            # Delete attendance
            AttendanceService.delete_attendance(attendance_id)
            
            # Return response
            return Response(
                json.dumps({'message': f'Attendance record {attendance_id} deleted successfully'}),
                status=204,
                content_type='application/json'
            )
            
        except Exception as e:
            return self._handle_error(e)
    
    @http.route('/api/v1/attendance/health', type='http', methods=['GET'], auth='public', csrf=False)
    def health_check(self, **kwargs):
        """Health check endpoint - no authentication required"""
        return Response(
            json.dumps({'status': 'healthy', 'message': 'Attendance API is running'}),
            status=200,
            content_type='application/json'
        )

