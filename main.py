import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, init_db

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Create the Flask app
app = Flask(__name__)

# Configure Flask app
app.secret_key = os.environ.get("SESSION_SECRET", "monthly-organics-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///monthly_organics.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
init_db(app)

# Import routes from app/main.py
from app.main import app as main_app

# Register the main app routes
@app.route('/')
def index():
    """Main index route that renders the homepage template."""
    try:
        logger.info("Rendering homepage")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        with app.app_context():
            db.engine.execute("SELECT 1")
        
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    logger.info("Starting Monthly Organics Flask application")
    logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(host='0.0.0.0', port=5000, debug=True)
