"""
Application factory for Monthly Organics
Creates and configures Flask application with blueprints
"""
import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config_by_name, Config
from models import db, init_db


def create_app(config_name=None):
    """Application factory function."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    
    # Load configuration
    config_class = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_class)
    
    # Validate configuration
    config_validation = Config.validate_config()
    if not config_validation['valid']:
        raise ValueError(f"Missing required configuration: {config_validation['missing']}")
    
    # Setup middleware
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG if app.config['DEBUG'] else logging.INFO)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def _register_blueprints(app):
    """Register all application blueprints."""
    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.store import store_bp
    from blueprints.addresses import addresses_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(addresses_bp)


def _register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        db.session.rollback()
        return render_template('errors/500.html'), 500