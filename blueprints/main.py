"""
Main blueprint for Monthly Organics
Handles core application routes
"""
import logging
from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main index route that renders the homepage template."""
    logger.info("Rendering homepage")
    return render_template('main/index.html')


@main_bp.route('/profile')
def profile():
    """Profile page route."""
    try:
        return render_template('main/profile.html')
    except Exception as e:
        logger.error(f"Error rendering profile page: {e}")
        return render_template('main/profile.html')


@main_bp.route('/orders')
def orders():
    """Orders page route - placeholder."""
    return render_template('main/profile.html')


@main_bp.route('/support')
def support():
    """Support page route - placeholder."""
    return render_template('main/profile.html')


@main_bp.route('/wallet')
def wallet():
    """Wallet page route - placeholder."""
    return render_template('main/profile.html')


@main_bp.route('/rewards')
def rewards():
    """Rewards page route - placeholder."""
    return render_template('main/profile.html')


@main_bp.route('/profile-settings')
def profile_settings():
    """Profile settings page route - placeholder."""
    return render_template('main/profile.html')


@main_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "message": "Monthly Organics is running"}