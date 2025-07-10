"""
Monthly Organics Application Entry Point
Clean application using blueprint architecture and improved structure
"""
from app import create_app

# Create application instance using factory pattern
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)