import os
import logging
import psycopg2
import psycopg2.extras
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
        
        # Connect to PostgreSQL database with DictCursor
        conn = psycopg2.connect(database_url)
        logging.info("Database connection established successfully")
        
        # Get cursor to execute table creation statements
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
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
        
        # Insert sample data if tables are empty
        cursor.execute("SELECT COUNT(*) FROM categories")
        result = cursor.fetchone()
        category_count = result[0] if result else 0
        
        if category_count == 0:
            # Insert sample categories
            categories_data = [
                ('Vegetables', '/static/icons/vegetables.svg'),
                ('Fruits', '/static/icons/fruits.svg'),
                ('Herbs', '/static/icons/herbs.svg'),
                ('Grains', '/static/icons/grains.svg'),
                ('Dairy', '/static/icons/dairy.svg'),
                ('Spices', '/static/icons/spices.svg')
            ]
            
            cursor.executemany(
                "INSERT INTO categories (name, icon_url) VALUES (%s, %s)",
                categories_data
            )
            
            # Insert sample products
            products_data = [
                ('Organic Spinach', 'Fresh organic spinach leaves, rich in iron and vitamins', 1, True),
                ('Fresh Carrots', 'Crisp organic carrots, perfect for cooking and salads', 1, True),
                ('Organic Tomatoes', 'Juicy red tomatoes, vine-ripened and pesticide-free', 1, True),
                ('Fresh Oranges', 'Sweet and tangy oranges, packed with vitamin C', 2, True),
                ('Organic Apples', 'Crisp red apples, naturally sweet and healthy', 2, False),
                ('Fresh Basil', 'Aromatic basil leaves, perfect for cooking', 3, True),
                ('Organic Rice', 'Premium quality brown rice, nutrient-rich', 4, False),
                ('Fresh Milk', 'Pure organic milk from grass-fed cows', 5, False),
                ('Turmeric Powder', 'Pure turmeric powder with anti-inflammatory properties', 6, False)
            ]
            
            cursor.executemany(
                "INSERT INTO products (name, description, category_id, is_best_seller) VALUES (%s, %s, %s, %s)",
                products_data
            )
            
            # Insert product variations
            variations_data = [
                (1, '250g', 45.00, 100),  # Spinach
                (1, '500g', 80.00, 50),
                (2, '1kg', 60.00, 75),    # Carrots
                (2, '2kg', 110.00, 30),
                (3, '500g', 80.00, 90),   # Tomatoes
                (3, '1kg', 150.00, 45),
                (4, '1kg', 120.00, 60),   # Oranges
                (4, '2kg', 220.00, 25),
                (5, '1kg', 180.00, 40),   # Apples
                (5, '2kg', 340.00, 20),
                (6, '50g', 35.00, 80),    # Basil
                (6, '100g', 65.00, 40),
                (7, '1kg', 95.00, 50),    # Rice
                (7, '5kg', 450.00, 20),
                (8, '500ml', 45.00, 30),  # Milk
                (8, '1L', 85.00, 25),
                (9, '100g', 25.00, 100),  # Turmeric
                (9, '250g', 55.00, 50)
            ]
            
            cursor.executemany(
                "INSERT INTO product_variations (product_id, variation_name, mrp, stock_quantity) VALUES (%s, %s, %s, %s)",
                variations_data
            )
            
            logging.info("Sample data inserted successfully")
        
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

@app.route('/store')
def store():
    """Store page route that displays categories and products."""
    try:
        conn = get_db_connection()
        if not conn:
            logging.error("Failed to connect to database")
            return render_template('store.html', categories=[])
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Fetch all categories with parameterized query
        cursor.execute("SELECT id, name, icon_url FROM categories ORDER BY name")
        categories = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logging.info(f"Fetched {len(categories)} categories for store page")
        return render_template('store.html', categories=categories)
        
    except Exception as e:
        logging.error(f"Error loading store page: {e}")
        return render_template('store.html', categories=[])

@app.route('/products/<int:category_id>')
def products_by_category(category_id):
    """HTMX route that returns products for a specific category."""
    try:
        conn = get_db_connection()
        if not conn:
            logging.error("Failed to connect to database")
            return render_template('partials/product_list.html', products=[])
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Fetch products with their variations using parameterized query
        query = """
        SELECT 
            p.id, p.name, p.description, p.is_best_seller,
            pv.id as variation_id, pv.variation_name, pv.mrp, pv.stock_quantity
        FROM products p
        LEFT JOIN product_variations pv ON p.id = pv.product_id
        WHERE p.category_id = %s
        ORDER BY p.is_best_seller DESC, p.name, pv.mrp
        """
        
        cursor.execute(query, (category_id,))
        results = cursor.fetchall()
        
        # Group variations by product
        products = {}
        for row in results:
            product_id = row['id']
            if product_id not in products:
                products[product_id] = {
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'is_best_seller': row['is_best_seller'],
                    'variations': []
                }
            
            if row['variation_id']:  # Only add if variation exists
                products[product_id]['variations'].append({
                    'id': row['variation_id'],
                    'name': row['variation_name'],
                    'price': float(row['mrp']),
                    'stock': row['stock_quantity']
                })
        
        products_list = list(products.values())
        
        cursor.close()
        conn.close()
        
        logging.info(f"Fetched {len(products_list)} products for category {category_id}")
        return render_template('partials/product_list.html', products=products_list)
        
    except Exception as e:
        logging.error(f"Error loading products for category {category_id}: {e}")
        return render_template('partials/product_list.html', products=[])

@app.route('/all-products')
def all_products():
    """Route that returns all products grouped by categories for the store page."""
    try:
        conn = get_db_connection()
        if not conn:
            logging.error("Failed to connect to database")
            return render_template('partials/all_products.html', categories_with_products=[])
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Fetch all categories with their products and variations
        query = """
        SELECT 
            c.id as category_id, c.name as category_name,
            p.id, p.name, p.description, p.is_best_seller,
            pv.id as variation_id, pv.variation_name, pv.mrp, pv.stock_quantity
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        LEFT JOIN product_variations pv ON p.id = pv.product_id
        ORDER BY c.name, p.is_best_seller DESC, p.name, pv.mrp
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Group data by category and then by product
        categories_data = {}
        for row in results:
            category_id = row['category_id']
            
            # Initialize category if not exists
            if category_id not in categories_data:
                categories_data[category_id] = {
                    'id': category_id,
                    'name': row['category_name'],
                    'products': {}
                }
            
            # If there's a product, add it
            if row['id']:
                product_id = row['id']
                if product_id not in categories_data[category_id]['products']:
                    categories_data[category_id]['products'][product_id] = {
                        'id': row['id'],
                        'name': row['name'],
                        'description': row['description'],
                        'is_best_seller': row['is_best_seller'],
                        'variations': []
                    }
                
                # Add variation if exists
                if row['variation_id']:
                    categories_data[category_id]['products'][product_id]['variations'].append({
                        'id': row['variation_id'],
                        'name': row['variation_name'],
                        'price': float(row['mrp']),
                        'stock': row['stock_quantity']
                    })
        
        # Convert to list format for template
        categories_with_products = []
        for category_data in categories_data.values():
            category_data['products'] = list(category_data['products'].values())
            categories_with_products.append(category_data)
        
        cursor.close()
        conn.close()
        
        logging.info(f"Fetched {len(categories_with_products)} categories with products")
        return render_template('partials/all_products.html', categories_with_products=categories_with_products)
        
    except Exception as e:
        logging.error(f"Error loading all products: {e}")
        return render_template('partials/all_products.html', categories_with_products=[])

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
