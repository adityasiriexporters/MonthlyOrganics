"""
Authentication blueprint for Monthly Organics
Handles all authentication-related routes
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from services.database import UserService
from utils.decorators import validate_mobile_number, validate_otp
from config import Config

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Mobile number login page."""
    return render_template('auth/login.html')


@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """Generate and send OTP for mobile number verification."""
    try:
        mobile_number = request.form.get('mobile_number', '').strip()
        
        if not validate_mobile_number(mobile_number):
            flash('Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.', 'error')
            return redirect(url_for('auth.login'))
        
        # Use configured testing OTP
        otp = Config.TESTING_OTP
        
        # Store OTP data in session
        session.update({
            'otp': otp,
            'mobile_number': mobile_number,
            'otp_attempts': 0
        })
        
        logger.info(f"OTP generated for {mobile_number}")
        return redirect(url_for('auth.verify'))
        
    except Exception as e:
        logger.error(f"Error sending OTP: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/verify')
def verify():
    """OTP verification page."""
    if not all(key in session for key in ['mobile_number', 'otp']):
        flash('Please start by entering your mobile number.', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/verify.html', 
                         mobile_number=session.get('mobile_number'))


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and login user."""
    try:
        # Validate session data
        if not all(key in session for key in ['mobile_number', 'otp']):
            flash('Session expired. Please start again.', 'error')
            return redirect(url_for('auth.login'))
        
        submitted_otp = request.form.get('otp', '').strip()
        stored_otp = session.get('otp')
        mobile_number = session.get('mobile_number')
        attempts = session.get('otp_attempts', 0)
        
        # Check attempt limits
        session['otp_attempts'] = attempts + 1
        if session['otp_attempts'] > Config.MAX_OTP_ATTEMPTS:
            session.clear()
            flash('Too many failed attempts. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Validate OTP format and value
        if not validate_otp(submitted_otp) or submitted_otp != stored_otp:
            remaining = Config.MAX_OTP_ATTEMPTS + 1 - session['otp_attempts']
            flash(f'Invalid OTP. You have {remaining} attempts remaining.', 'error')
            return redirect(url_for('auth.verify'))
        
        # Find or create user
        user = UserService.find_user_by_phone(mobile_number)
        if not user:
            user = UserService.create_user(mobile_number)
            if not user:
                flash('Error creating user account. Please try again.', 'error')
                return redirect(url_for('auth.login'))
        
        # Login successful
        session['user_id'] = user['id'] if isinstance(user, dict) else user.id
        
        # Clear authentication session data
        for key in ['otp', 'mobile_number', 'otp_attempts']:
            session.pop(key, None)
        
        flash('Login successful!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('auth.verify'))


@auth_bp.route('/logout')
def logout():
    """Logout user by clearing session."""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('main.index'))