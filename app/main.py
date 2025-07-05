import os
import logging
import psycopg2
from flask import Flask, render_template, request

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Set secret key from environment variable
app.secret_key = os.environ.get("SESSION_SECRET", "monthly-organics-secret-key")

def get_db_connection():
    """
    Connect to PostgreSQL database using psycopg2-binary library.
    Reads the full database connection URL from DATABASE_URL environment variable.
    Creates e-commerce tables if they don't exist.
    """
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logging.error("DATABASE_URL environment variable not set")
            return None
        
        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url)
        logging.info("Database connection established successfully")
        
        # Get cursor to execute table creation statements
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        create_tables_sql = [
            # Users table
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                mobile_number VARCHAR(15) UNIQUE NOT NULL,
                wallet_balance DECIMAL(10, 2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Categories table
            """
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                icon_url VARCHAR(500)
            );
            """,
            
            # Products table
            """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                is_best_seller BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Product variations table
            """
            CREATE TABLE IF NOT EXISTS product_variations (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                variation_name VARCHAR(100) NOT NULL,
                mrp DECIMAL(10, 2) NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
        
        # Execute all CREATE TABLE statements
        for sql in create_tables_sql:
            cursor.execute(sql)
        
        # Commit the changes
        conn.commit()
        logging.info("E-commerce database tables created successfully")
        
        # Close the cursor
        cursor.close()
        
        return conn
        
    except psycopg2.Error as e:
        logging.error(f"Database connection or table creation failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error connecting to database: {e}")
        return None

@app.route('/')
def index():
    """Main index route that renders the homepage template."""
    try:
        # Test database connection
        conn = get_db_connection()
        if conn:
            conn.close()
            logging.info("Database connection test successful")
        
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Error rendering index page: {e}")
        return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            return {"status": "healthy", "database": "connected"}, 200
        else:
            return {"status": "unhealthy", "database": "disconnected"}, 500
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
