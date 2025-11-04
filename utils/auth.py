"""
Authentication utilities and decorators for SecureGuard Fraud Detection System
"""

from functools import wraps
from flask import redirect, url_for, flash, request, session
from flask_login import current_user
import jwt
from datetime import datetime, timedelta
import os

# JWT Secret Key (should be in environment variable in production)
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'secureguard-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_token(user_id, username, role):
    """
    Generate JWT token for authenticated user

    Args:
        user_id: User's unique ID
        username: User's username
        role: User's role (admin, analyst, viewer)

    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token):
    """
    Decode and verify JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


def login_required(f):
    """
    Decorator to require user login for a route

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "This is protected"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator to require specific role(s) for a route

    Args:
        *roles: One or more role names (admin, analyst, viewer)

    Usage:
        @app.route('/admin')
        @login_required
        @role_required('admin')
        def admin_only():
            return "Admin only"

        @app.route('/analysis')
        @login_required
        @role_required('admin', 'analyst')
        def analyst_or_admin():
            return "Analysts and admins"
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))

            if current_user.role not in roles:
                flash(f'Access denied. Required role: {", ".join(roles)}', 'danger')
                return redirect(url_for('home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(*permissions):
    """
    Decorator to require specific permission(s) for a route

    Args:
        *permissions: One or more permission names

    Usage:
        @app.route('/delete')
        @login_required
        @permission_required('delete')
        def delete_item():
            return "Can delete"
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))

            user_permissions = current_user.get_permissions()
            has_permission = any(perm in user_permissions for perm in permissions)

            if not has_permission:
                flash(f'Access denied. Required permission: {", ".join(permissions)}', 'danger')
                return redirect(url_for('home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to require admin role
    Shorthand for @role_required('admin')

    Usage:
        @app.route('/admin/users')
        @login_required
        @admin_required
        def manage_users():
            return "Admin only"
    """
    return role_required('admin')(f)


def get_client_ip():
    """Get client's IP address from request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    return request.environ.get('REMOTE_ADDR', 'Unknown')


def get_user_agent():
    """Get client's user agent from request"""
    return request.headers.get('User-Agent', 'Unknown')


def validate_password_strength(password):
    """
    Validate password strength

    Requirements:
    - At least 8 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains digit
    - Contains special character

    Args:
        password: Password string to validate

    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    return True, "Password is strong"


def sanitize_username(username):
    """
    Sanitize username input

    Args:
        username: Raw username string

    Returns:
        Sanitized username
    """
    # Remove leading/trailing whitespace
    username = username.strip()

    # Convert to lowercase
    username = username.lower()

    # Remove any non-alphanumeric characters except underscore and hyphen
    import re
    username = re.sub(r'[^a-z0-9_-]', '', username)

    return username


def generate_session_token():
    """Generate a secure random session token"""
    import secrets
    return secrets.token_urlsafe(32)


class RateLimiter:
    """Simple in-memory rate limiter for login attempts"""

    def __init__(self, max_attempts=5, window_minutes=15):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.attempts = {}  # {ip_address: [(timestamp, success), ...]}

    def is_rate_limited(self, ip_address):
        """Check if IP address is rate limited"""
        if ip_address not in self.attempts:
            return False

        # Clean old attempts
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        self.attempts[ip_address] = [
            (ts, success) for ts, success in self.attempts[ip_address]
            if ts > cutoff_time
        ]

        # Count failed attempts
        failed_attempts = sum(1 for _, success in self.attempts[ip_address] if not success)

        return failed_attempts >= self.max_attempts

    def record_attempt(self, ip_address, success):
        """Record a login attempt"""
        if ip_address not in self.attempts:
            self.attempts[ip_address] = []

        self.attempts[ip_address].append((datetime.now(), success))

        # Keep only recent attempts
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        self.attempts[ip_address] = [
            (ts, success) for ts, success in self.attempts[ip_address]
            if ts > cutoff_time
        ]

    def get_remaining_attempts(self, ip_address):
        """Get number of remaining login attempts"""
        if ip_address not in self.attempts:
            return self.max_attempts

        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        failed_attempts = sum(
            1 for ts, success in self.attempts[ip_address]
            if not success and ts > cutoff_time
        )

        return max(0, self.max_attempts - failed_attempts)


# Global rate limiter instance
login_rate_limiter = RateLimiter(max_attempts=5, window_minutes=15)
