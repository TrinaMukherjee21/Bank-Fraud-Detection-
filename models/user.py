"""
User Model for SecureGuard Fraud Detection System
Handles user authentication, authorization, and activity logging
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class User(UserMixin):
    """
    User model with role-based access control

    Roles:
    - Admin: Full access (manage users, view all analytics, configure system)
    - Analyst: Read/write access (analyze transactions, view analytics)
    - Viewer: Read-only access (view dashboard and reports)
    """

    ROLES = {
        'admin': {
            'level': 3,
            'permissions': ['create', 'read', 'update', 'delete', 'manage_users', 'configure_system'],
            'description': 'Full system access with user management'
        },
        'analyst': {
            'level': 2,
            'permissions': ['create', 'read', 'update', 'analyze_transactions'],
            'description': 'Can analyze transactions and view analytics'
        },
        'viewer': {
            'level': 1,
            'permissions': ['read'],
            'description': 'Read-only access to dashboard and reports'
        }
    }

    def __init__(self, user_id=None, username=None, email=None, password_hash=None,
                 role='viewer', is_active=True, created_at=None, last_login=None):
        self.id = user_id or str(uuid.uuid4())
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role if role in self.ROLES else 'viewer'
        self._is_active = is_active  # Use internal attribute to avoid conflict with UserMixin
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.failed_login_attempts = 0
        self.locked_until = None

    @property
    def is_active(self):
        """Flask-Login required property"""
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        """Allow setting is_active"""
        self._is_active = value

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        """Verify the user's password"""
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        """Check if user has a specific permission"""
        role_permissions = self.ROLES.get(self.role, {}).get('permissions', [])
        return permission in role_permissions

    def has_role(self, role):
        """Check if user has a specific role"""
        return self.role == role

    def has_role_level(self, min_level):
        """Check if user's role level meets minimum requirement"""
        user_level = self.ROLES.get(self.role, {}).get('level', 0)
        return user_level >= min_level

    def get_permissions(self):
        """Get list of user's permissions"""
        return self.ROLES.get(self.role, {}).get('permissions', [])

    def get_role_description(self):
        """Get description of user's role"""
        return self.ROLES.get(self.role, {}).get('description', 'Unknown role')

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now()
        self.failed_login_attempts = 0
        self.locked_until = None

    def increment_failed_login(self):
        """Increment failed login attempts and lock account if needed"""
        self.failed_login_attempts += 1

        # Lock account for 15 minutes after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = datetime.now() + timedelta(minutes=15)
            return True  # Account locked
        return False

    def is_locked(self):
        """Check if account is currently locked"""
        if self.locked_until:
            if datetime.now() < self.locked_until:
                return True
            else:
                # Lock period expired, reset
                self.locked_until = None
                self.failed_login_attempts = 0
        return False

    def to_dict(self):
        """Convert user object to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'role_description': self.get_role_description(),
            'permissions': self.get_permissions(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class UserActivityLog:
    """Log user activities for audit trail"""

    def __init__(self, user_id, action, details=None, ip_address=None, user_agent=None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.action = action
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = datetime.now()

    def to_dict(self):
        """Convert activity log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat()
        }

    def __repr__(self):
        return f'<UserActivity {self.action} by {self.user_id} at {self.timestamp}>'


# In-memory user storage (for demonstration - replace with database in production)
class UserStore:
    """Simple in-memory user storage"""

    def __init__(self):
        self.users = {}
        self.activity_logs = []
        self._create_default_users()

    def _create_default_users(self):
        """Create default admin and demo users"""
        # Admin user
        admin = User(
            user_id='admin-001',
            username='admin',
            email='admin@secureguard.com',
            role='admin'
        )
        admin.set_password('admin123')  # Change in production!
        self.users[admin.id] = admin

        # Analyst user
        analyst = User(
            user_id='analyst-001',
            username='analyst',
            email='analyst@secureguard.com',
            role='analyst'
        )
        analyst.set_password('analyst123')  # Change in production!
        self.users[analyst.id] = analyst

        # Viewer user
        viewer = User(
            user_id='viewer-001',
            username='viewer',
            email='viewer@secureguard.com',
            role='viewer'
        )
        viewer.set_password('viewer123')  # Change in production!
        self.users[viewer.id] = viewer

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        return self.users.get(user_id)

    def get_user_by_username(self, username):
        """Get user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def get_user_by_email(self, email):
        """Get user by email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def add_user(self, user):
        """Add a new user"""
        if user.id in self.users:
            raise ValueError(f"User with ID {user.id} already exists")
        if self.get_user_by_username(user.username):
            raise ValueError(f"Username {user.username} already exists")
        if self.get_user_by_email(user.email):
            raise ValueError(f"Email {user.email} already exists")

        self.users[user.id] = user
        return user

    def update_user(self, user):
        """Update existing user"""
        if user.id not in self.users:
            raise ValueError(f"User with ID {user.id} not found")
        self.users[user.id] = user
        return user

    def delete_user(self, user_id):
        """Delete user by ID"""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False

    def get_all_users(self):
        """Get all users"""
        return list(self.users.values())

    def log_activity(self, user_id, action, details=None, ip_address=None, user_agent=None):
        """Log user activity"""
        activity = UserActivityLog(user_id, action, details, ip_address, user_agent)
        self.activity_logs.append(activity)

        # Keep only last 1000 logs
        if len(self.activity_logs) > 1000:
            self.activity_logs = self.activity_logs[-1000:]

        return activity

    def get_user_activity(self, user_id, limit=50):
        """Get recent activity for a user"""
        user_logs = [log for log in self.activity_logs if log.user_id == user_id]
        return user_logs[-limit:]

    def get_all_activity(self, limit=100):
        """Get recent activity for all users"""
        return self.activity_logs[-limit:]


# Global user store instance
user_store = UserStore()
