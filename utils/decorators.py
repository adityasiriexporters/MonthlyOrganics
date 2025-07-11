"""
Custom decorators for Monthly Organics application
"""
import logging
from functools import wraps
from flask import session, request, redirect, url_for, make_response

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to require login for certain routes with improved HTMX handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Login check - Session data: {dict(session)}")
        logger.debug(f"Login check - Request headers: {dict(request.headers)}")
        
        if 'user_id' not in session:
            logger.warning(f"No user_id in session for {request.endpoint}")
            # For HTMX requests, use HX-Redirect header to redirect the entire page
            if request.headers.get('HX-Request'):
                response = make_response('Login required', 401)
                response.headers['HX-Redirect'] = url_for('login')
                return response
            else:
                return redirect(url_for('login'))
        
        logger.debug(f"User {session['user_id']} accessing {request.endpoint}")
        return f(*args, **kwargs)
    return decorated_function

def validate_mobile_number(mobile_number: str) -> bool:
    """Validate Indian mobile number format"""
    import re
    return bool(mobile_number and re.match(r'^[6-9]\d{9}$', mobile_number))

def validate_otp(otp: str) -> bool:
    """Validate OTP format"""
    import re
    return bool(otp and re.match(r'^\d{6}$', otp))