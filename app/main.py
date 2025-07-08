import os
import logging
import psycopg2
import psycopg2.extras
import random
import re
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash

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
            # Users table (matches models.py structure)
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(120) UNIQUE NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE NOT NULL
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
            """,
            
            # Cart items table
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                variation_id INTEGER REFERENCES product_variations(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL,
                UNIQUE(user_id, variation_id)
            );
            """,
            
            # Orders table
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                total_amount DECIMAL(10, 2) NOT NULL,
                shipping_address TEXT NOT NULL,
                order_status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Order items table
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                variation_id INTEGER REFERENCES product_variations(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL,
                price_at_purchase DECIMAL(10, 2) NOT NULL
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

def login_required(f):
    """Decorator to require login for certain routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # For HTMX requests, use HX-Redirect header to redirect the entire page
            if request.headers.get('HX-Request'):
                response = jsonify({'error': 'Login required'})
                response.headers['HX-Redirect'] = url_for('login')
                return response, 401
            else:
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Mobile number login page."""
    return render_template('login.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Generate and send OTP for mobile number verification."""
    try:
        mobile_number = request.form.get('mobile_number', '').strip()
        
        # Validate mobile number format (10 digits)
        if not mobile_number or not re.match(r'^[6-9]\d{9}$', mobile_number):
            flash('Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.', 'error')
            return redirect(url_for('login'))
        
        # Generate 6-digit OTP
        otp = random.randint(100000, 999999)
        
        # Store OTP and mobile number in session
        session['otp'] = str(otp)
        session['mobile_number'] = mobile_number
        session['otp_attempts'] = 0
        
        # For testing - print OTP to console (will be replaced with MSG91 API later)
        print(f"OTP for {mobile_number} is: {otp}")
        
        return redirect(url_for('verify'))
        
    except Exception as e:
        logging.error(f"Error sending OTP: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/verify')
def verify():
    """OTP verification page."""
    if 'mobile_number' not in session or 'otp' not in session:
        flash('Please start by entering your mobile number.', 'error')
        return redirect(url_for('login'))
    
    mobile_number = session.get('mobile_number')
    return render_template('verify.html', mobile_number=mobile_number)

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and login user."""
    try:
        if 'mobile_number' not in session or 'otp' not in session:
            flash('Session expired. Please start again.', 'error')
            return redirect(url_for('login'))
        
        submitted_otp = request.form.get('otp', '').strip()
        stored_otp = session.get('otp')
        mobile_number = session.get('mobile_number')
        attempts = session.get('otp_attempts', 0)
        
        # Increment attempt counter
        session['otp_attempts'] = attempts + 1
        
        # Check for too many attempts
        if session['otp_attempts'] > 3:
            # Clear session and redirect to login
            session.clear()
            flash('Too many failed attempts. Please try again.', 'error')
            return redirect(url_for('login'))
        
        # Validate OTP format
        if not submitted_otp or not re.match(r'^\d{6}$', submitted_otp):
            flash('Please enter a valid 6-digit OTP.', 'error')
            return redirect(url_for('verify'))
        
        # Verify OTP
        if submitted_otp != stored_otp:
            flash(f'Invalid OTP. You have {4 - session["otp_attempts"]} attempts remaining.', 'error')
            return redirect(url_for('verify'))
        
        # OTP is correct - find or create user
        conn = get_db_connection()
        if not conn:
            flash('Database connection error. Please try again.', 'error')
            return redirect(url_for('verify'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Check if user exists
        cursor.execute("SELECT id, name FROM users WHERE mobile_number = %s", (mobile_number,))
        user = cursor.fetchone()
        
        if user:
            user_id = user['id']
            logging.info(f"Existing user logged in: {mobile_number}")
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (name, mobile_number) VALUES (%s, %s) RETURNING id",
                (f"User {mobile_number[-4:]}", mobile_number)  # Use last 4 digits as default name
            )
            user_id = cursor.fetchone()['id']
            conn.commit()
            logging.info(f"New user created: {mobile_number}")
        
        # Login user
        session['user_id'] = user_id
        
        # Clear OTP data from session
        session.pop('otp', None)
        session.pop('mobile_number', None)
        session.pop('otp_attempts', None)
        
        cursor.close()
        conn.close()
        
        flash('Login successful!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logging.error(f"Error verifying OTP: {e}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('verify'))

@app.route('/logout')
def logout():
    """Logout user by clearing session."""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/add-to-cart/<int:variation_id>', methods=['POST'])
@login_required
def add_to_cart(variation_id):
    """Add item to cart or update quantity if already exists."""
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if not conn:
            return "Database connection failed", 500
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Use UPSERT to add item or update quantity
        cursor.execute("""
            INSERT INTO cart_items (user_id, variation_id, quantity)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, variation_id)
            DO UPDATE SET quantity = cart_items.quantity + 1
            RETURNING quantity
        """, (user_id, variation_id))
        
        new_quantity = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        # Return quantity stepper HTML
        return f'''
        <div class="flex items-center space-x-2 bg-green-100 border border-green-300 rounded-lg px-3 py-1">
            <button hx-post="/update-cart/{variation_id}/decr" 
                    hx-swap="outerHTML"
                    class="w-8 h-8 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors">
                -
            </button>
            <span class="px-2 font-semibold text-green-800">{new_quantity}</span>
            <button hx-post="/update-cart/{variation_id}/incr" 
                    hx-swap="outerHTML"
                    class="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center hover:bg-green-600 transition-colors">
                +
            </button>
        </div>
        '''
        
    except Exception as e:
        logging.error(f"Error adding to cart: {e}")
        return "Error adding to cart", 500

@app.route('/update-cart/<int:variation_id>/<string:action>', methods=['POST'])
@login_required
def update_cart(variation_id, action):
    """Update cart item quantity (increment or decrement)."""
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if not conn:
            return "Database connection failed", 500
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if action == 'incr':
            cursor.execute("""
                UPDATE cart_items 
                SET quantity = quantity + 1 
                WHERE user_id = %s AND variation_id = %s
                RETURNING quantity
            """, (user_id, variation_id))
        elif action == 'decr':
            cursor.execute("""
                UPDATE cart_items 
                SET quantity = quantity - 1 
                WHERE user_id = %s AND variation_id = %s
                RETURNING quantity
            """, (user_id, variation_id))
        else:
            return "Invalid action", 400
            
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return "Item not found in cart", 404
            
        new_quantity = result[0]
        
        # If quantity becomes 0, delete the item
        if new_quantity <= 0:
            cursor.execute("""
                DELETE FROM cart_items 
                WHERE user_id = %s AND variation_id = %s
            """, (user_id, variation_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Return add to cart button
            return f'''
            <button hx-post="/add-to-cart/{variation_id}" 
                    hx-swap="outerHTML"
                    class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                Add to Cart
            </button>
            '''
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Return updated quantity stepper
        return f'''
        <div class="flex items-center space-x-2 bg-green-100 border border-green-300 rounded-lg px-3 py-1">
            <button hx-post="/update-cart/{variation_id}/decr" 
                    hx-swap="outerHTML"
                    class="w-8 h-8 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors">
                -
            </button>
            <span class="px-2 font-semibold text-green-800">{new_quantity}</span>
            <button hx-post="/update-cart/{variation_id}/incr" 
                    hx-swap="outerHTML"
                    class="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center hover:bg-green-600 transition-colors">
                +
            </button>
        </div>
        '''
        
    except Exception as e:
        logging.error(f"Error updating cart: {e}")
        return "Error updating cart", 500

@app.route('/cart')
@login_required
def cart():
    """Display user's shopping cart."""
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if not conn:
            return render_template('cart.html', cart_items=[], total_amount=0)
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get cart items with product and variation details
        cursor.execute("""
            SELECT 
                ci.variation_id,
                ci.quantity,
                p.name as product_name,
                p.description as product_description,
                pv.variation_name,
                pv.mrp,
                (ci.quantity * pv.mrp) as line_total
            FROM cart_items ci
            JOIN product_variations pv ON ci.variation_id = pv.id
            JOIN products p ON pv.product_id = p.id
            WHERE ci.user_id = %s
            ORDER BY p.name, pv.variation_name
        """, (user_id,))
        
        cart_items = cursor.fetchall()
        
        # Calculate total
        total_amount = sum(float(item['line_total']) for item in cart_items)
        
        cursor.close()
        conn.close()
        
        return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)
        
    except Exception as e:
        logging.error(f"Error loading cart: {e}")
        return render_template('cart.html', cart_items=[], total_amount=0)

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
