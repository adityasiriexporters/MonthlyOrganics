"""
Admin authentication system for Monthly Organics
Separate authentication mechanism for administrative access
"""

from functools import wraps
from flask import session, redirect, url_for, request, flash
import hashlib
import hmac

class AdminAuth:
    """Admin authentication handler"""
    
    # Hardcoded admin credentials (in production, use environment variables)
    ADMIN_CREDENTIALS = {
        'akhil@monthlyorganics.com': 'Asdf@123'
    }
    
    @classmethod
    def verify_admin_credentials(cls, username: str, password: str) -> bool:
        """Verify admin login credentials"""
        if username in cls.ADMIN_CREDENTIALS:
            return cls.ADMIN_CREDENTIALS[username] == password
        return False
    
    @classmethod
    def login_admin(cls, username: str) -> bool:
        """Login admin user and set session"""
        session['admin_user'] = username
        session['is_admin'] = True
        return True
    
    @classmethod
    def logout_admin(cls):
        """Logout admin user and clear session"""
        session.pop('admin_user', None)
        session.pop('is_admin', None)
    
    @classmethod
    def is_admin_logged_in(cls) -> bool:
        """Check if admin is logged in"""
        return session.get('is_admin', False)
    
    @classmethod
    def get_admin_user(cls) -> str:
        """Get current admin username"""
        return session.get('admin_user', '')

def admin_required(f):
    """Decorator to protect admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AdminAuth.is_admin_logged_in():
            flash('Admin access required. Please login.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function