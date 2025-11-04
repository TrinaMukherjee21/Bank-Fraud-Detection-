"""
Comprehensive security module for bank-ready fraud detection system.

This module provides enterprise-grade security features including:
- API key management and authentication
- Request signing and validation
- CSRF protection
- Input sanitization
- Security headers
- Audit logging
"""

import hashlib
import hmac
import secrets
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from flask import request, jsonify, session, g, current_app
import re
from datetime import datetime, timedelta
# import jwt  # Not currently used

logger = logging.getLogger(__name__)

class SecurityManager:
    """Centralized security management for fraud detection system"""
    
    def __init__(self, app=None):
        self.app = app
        self.api_keys = {}  # Store API keys in production database
        self.blocked_ips = set()
        self.request_history = {}  # Track request patterns
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security manager with Flask app"""
        app.config.setdefault('SECRET_KEY', secrets.token_urlsafe(32))
        app.config.setdefault('API_KEY_EXPIRY_HOURS', 24)
        app.config.setdefault('MAX_REQUEST_SIZE', 1024 * 1024)  # 1MB
        app.config.setdefault('SIGNATURE_ALGORITHM', 'sha256')
        
        # Security headers middleware
        @app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            return response
        
        # Request validation middleware
        @app.before_request
        def validate_request():
            # Check IP blocking
            client_ip = self.get_client_ip()
            if client_ip in self.blocked_ips:
                logger.warning(f"Blocked IP attempted access: {client_ip}")
                return jsonify({'error': 'Access denied'}), 403
            
            # Rate limiting per IP
            if not self.check_rate_limit(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Content-length validation
            if request.content_length and request.content_length > current_app.config['MAX_REQUEST_SIZE']:
                logger.warning(f"Request too large from {client_ip}: {request.content_length}")
                return jsonify({'error': 'Request too large'}), 413
    
    def get_client_ip(self) -> str:
        """Get real client IP address"""
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        elif request.headers.get("X-Real-Ip"):
            ip = request.headers.get("X-Real-Ip")
        else:
            ip = request.remote_addr
        return ip or "unknown"
    
    def check_rate_limit(self, ip: str, max_requests: int = 100, window_minutes: int = 60) -> bool:
        """Check if IP is within rate limits"""
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=window_minutes)
        
        if ip not in self.request_history:
            self.request_history[ip] = []
        
        # Clean old requests
        self.request_history[ip] = [
            req_time for req_time in self.request_history[ip] 
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.request_history[ip]) >= max_requests:
            return False
        
        # Record this request
        self.request_history[ip].append(current_time)
        return True
    
    def generate_api_key(self, user_id: str, permissions: list = None) -> Tuple[str, str]:
        """Generate secure API key pair"""
        key_id = secrets.token_urlsafe(16)
        secret = secrets.token_urlsafe(32)
        
        # Store key metadata
        self.api_keys[key_id] = {
            'secret_hash': hashlib.sha256(secret.encode()).hexdigest(),
            'user_id': user_id,
            'permissions': permissions or ['predict'],
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
            'active': True
        }
        
        logger.info(f"Generated API key for user: {user_id}")
        return key_id, secret
    
    def validate_api_key(self, key_id: str, secret: str) -> Tuple[bool, Optional[Dict]]:
        """Validate API key and return user info"""
        if key_id not in self.api_keys:
            return False, None
        
        key_data = self.api_keys[key_id]
        
        # Check if key is active
        if not key_data['active']:
            return False, None
        
        # Check expiration
        if datetime.fromisoformat(key_data['expires_at']) < datetime.now():
            key_data['active'] = False
            return False, None
        
        # Validate secret
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        if not hmac.compare_digest(key_data['secret_hash'], secret_hash):
            return False, None
        
        return True, key_data

def require_api_key(permissions: list = None):
    """Decorator to require valid API key for access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid authorization header'}), 401
            
            try:
                # Parse API key from header
                token = auth_header[7:]  # Remove 'Bearer ' prefix
                key_id, secret = token.split(':', 1)
                
                # Validate key
                security_manager = current_app.extensions.get('security_manager')
                if not security_manager:
                    return jsonify({'error': 'Security not configured'}), 500
                
                valid, key_data = security_manager.validate_api_key(key_id, secret)
                if not valid:
                    logger.warning(f"Invalid API key attempted: {key_id}")
                    return jsonify({'error': 'Invalid API key'}), 401
                
                # Check permissions
                if permissions:
                    user_permissions = key_data.get('permissions', [])
                    if not any(perm in user_permissions for perm in permissions):
                        return jsonify({'error': 'Insufficient permissions'}), 403
                
                # Store user info for request
                g.api_user = key_data
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"API key validation error: {str(e)}")
                return jsonify({'error': 'Authentication failed'}), 401
        
        return decorated_function
    return decorator

def sign_request(payload: Dict[str, Any], secret: str) -> str:
    """Generate HMAC signature for request payload"""
    message = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return signature

def verify_signature(payload: Dict[str, Any], signature: str, secret: str) -> bool:
    """Verify HMAC signature for request payload"""
    expected_signature = sign_request(payload, secret)
    return hmac.compare_digest(signature, expected_signature)

def require_signature():
    """Decorator to require valid HMAC signature"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            signature = request.headers.get('X-Signature')
            if not signature:
                return jsonify({'error': 'Missing signature'}), 400
            
            try:
                payload = request.get_json()
                if not payload:
                    return jsonify({'error': 'Invalid JSON payload'}), 400
                
                # Get API key from context
                if not hasattr(g, 'api_user'):
                    return jsonify({'error': 'Authentication required'}), 401
                
                # Verify signature (using a derived key)
                secret = current_app.config['SECRET_KEY']
                if not verify_signature(payload, signature, secret):
                    logger.warning("Invalid signature detected")
                    return jsonify({'error': 'Invalid signature'}), 400
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Signature verification error: {str(e)}")
                return jsonify({'error': 'Signature verification failed'}), 400
        
        return decorated_function
    return decorator

def sanitize_input(data: Any) -> Any:
    """Recursively sanitize input data"""
    if isinstance(data, str):
        # Remove potentially dangerous characters
        data = re.sub(r'[<>"\';()&+]', '', data)
        # Limit length
        data = data[:1000] if len(data) > 1000 else data
        return data.strip()
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data

def validate_transaction_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate transaction data for fraud detection"""
    required_fields = ['step', 'amount', 'gender', 'category']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate field types and ranges
    try:
        step = int(data['step'])
        if step < 1 or step > 10000:
            return False, "Step must be between 1 and 10000"
        
        amount = float(data['amount'])
        if amount <= 0 or amount > 10000000:  # 10M limit
            return False, "Amount must be positive and less than 10,000,000"
        
        gender = int(data['gender'])
        if gender not in [0, 1]:
            return False, "Gender must be 0 or 1"
        
        category = int(data['category'])
        if category < 0 or category > 20:
            return False, "Category must be between 0 and 20"
        
        # Optional fields validation
        if 'customer' in data:
            customer = int(data['customer'])
            if customer < 0:
                return False, "Customer ID must be non-negative"
        
        if 'age' in data:
            age = int(data['age'])
            if age < 0 or age > 10:
                return False, "Age group must be between 0 and 10"
        
        return True, "Valid"
        
    except (ValueError, TypeError) as e:
        return False, f"Invalid data type: {str(e)}"

def generate_csrf_token() -> str:
    """Generate CSRF token for session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']

def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token"""
    session_token = session.get('csrf_token')
    if not session_token:
        return False
    return hmac.compare_digest(session_token, token)

def require_csrf():
    """Decorator to require valid CSRF token"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
                if not token or not validate_csrf_token(token):
                    logger.warning("Invalid CSRF token detected")
                    return jsonify({'error': 'Invalid CSRF token'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class AuditLogger:
    """Enhanced audit logging for compliance"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def log_action(self, action_type: str, user_id: str = None, 
                  entity_type: str = None, entity_id: str = None,
                  details: Dict[str, Any] = None, ip_address: str = None):
        """Log user action for audit trail"""
        try:
            log_entry = {
                'session_id': session.get('session_id', 'system'),
                'user_id': user_id or session.get('user_id'),
                'action_type': action_type,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'details': json.dumps(details) if details else None,
                'ip_address': ip_address or self.get_client_ip(),
                'user_agent': request.headers.get('User-Agent', '')[:500] if request else None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store in database (implementation depends on database_config.py)
            self.db.log_audit_entry(log_entry)
            
            logger.info(f"Audit log: {action_type} by {user_id} from {log_entry['ip_address']}")
            
        except Exception as e:
            logger.error(f"Failed to log audit entry: {str(e)}")
    
    def get_client_ip(self) -> str:
        """Get client IP address"""
        if request.headers.getlist("X-Forwarded-For"):
            return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        return request.remote_addr or "unknown"

def init_security(app, db_manager):
    """Initialize security components with Flask app"""
    security_manager = SecurityManager(app)
    audit_logger = AuditLogger(db_manager)
    
    # Store in app extensions
    app.extensions['security_manager'] = security_manager
    app.extensions['audit_logger'] = audit_logger
    
    # Add template globals
    @app.template_global()
    def csrf_token():
        return generate_csrf_token()
    
    return security_manager, audit_logger