import os
import logging
import psycopg2
import psycopg2.extras
import random
import re
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, init_db

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()

@app.route('/')
def index():
    """Main index route that renders the homepage template."""
    logger.info("Rendering homepage")
    return render_template('index.html')

@app.route('/profile')
def profile():
    """Profile page route."""
    try:
        return render_template('profile.html')
    except Exception as e:
        logger.error(f"Error rendering profile page: {e}")
        return render_template('profile.html')

def get_db_connection():
    """Get database connection using environment variable."""
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logging.error("DATABASE_URL environment variable not set")
            return None
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return None

def login_required(f):
    """Decorator to require login for certain routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logging.debug(f"Login check - Session data: {dict(session)}")
        logging.debug(f"Login check - Request headers: {dict(request.headers)}")
        
        if 'user_id' not in session:
            logging.warning(f"No user_id in session for {request.endpoint}")
            # For HTMX requests, use HX-Redirect header to redirect the entire page
            if request.headers.get('HX-Request'):
                from flask import make_response
                response = make_response('Login required', 401)
                response.headers['HX-Redirect'] = url_for('login')
                return response
            else:
                return redirect(url_for('login'))
        
        logging.debug(f"User {session['user_id']} accessing {request.endpoint}")
        return f(*args, **kwargs)
    return decorated_function

# Import store functions from app/main.py
from app.main import store as store_view, products_by_category, all_products

# Store routes 
app.add_url_rule('/store', 'store', store_view, methods=['GET'])
app.add_url_rule('/products/<int:category_id>', 'products_by_category', products_by_category, methods=['GET'])
app.add_url_rule('/all-products', 'all_products', all_products, methods=['GET'])

@app.route('/cart')
@login_required
def cart():
    """Display user's shopping cart."""
    try:
        user_id = session['user_id']
        logging.info(f"Cart page accessed by user_id: {user_id}")
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed. Please try again.', 'error')
            return redirect(url_for('index'))
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get cart items with product details
        cursor.execute("""
            SELECT 
                ci.variation_id,
                ci.quantity,
                pv.variation_name,
                pv.mrp as price,
                p.name as product_name,
                p.description,
                (ci.quantity * pv.mrp) as total_price
            FROM cart_items ci
            JOIN product_variations pv ON ci.variation_id = pv.id
            JOIN products p ON pv.product_id = p.id
            WHERE ci.user_id = %s
            ORDER BY p.name, pv.variation_name
        """, (user_id,))
        
        cart_items = cursor.fetchall()
        logging.info(f"Found {len(cart_items)} cart items for user {user_id}")
        
        # Calculate cart totals
        from decimal import Decimal
        subtotal = sum(item['total_price'] for item in cart_items)
        delivery_fee = Decimal('50.00') if subtotal > 0 else Decimal('0.00')  # ₹50 delivery fee
        total = subtotal + delivery_fee
        
        cursor.close()
        conn.close()
        
        return render_template('cart.html', 
                             cart_items=cart_items,
                             subtotal=subtotal,
                             delivery_fee=delivery_fee,
                             total=total)
        
    except Exception as e:
        logging.error(f"Error loading cart: {e}")
        flash('Error loading cart. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/orders')
def orders():
    """Orders page route - placeholder."""
    return "<h1>Your Orders - Coming Soon</h1><p>Order history will be available here.</p>"

@app.route('/support')
def support():
    """Support page route - placeholder."""
    return "<h1>Customer Support - Coming Soon</h1><p>Support chat will be available here.</p>"

@app.route('/wallet')
def wallet():
    """Wallet page route - placeholder."""
    return "<h1>Wallet - Coming Soon</h1><p>Wallet balance and transactions will be shown here.</p>"

@app.route('/rewards')
def rewards():
    """Rewards page route - placeholder."""
    return "<h1>Rewards - Coming Soon</h1><p>Loyalty points and rewards will be displayed here.</p>"

@app.route('/profile/settings')
def profile_settings():
    """Profile settings page route - placeholder."""
    return "<h1>Profile Settings - Coming Soon</h1><p>Update your profile information here.</p>"

@app.route('/addresses')
def addresses():
    """Addresses page route - placeholder."""
    return "<h1>Saved Addresses - Coming Soon</h1><p>Manage your delivery addresses here.</p>"

@app.route('/addresses/add')
def add_address():
    """Add address page route - placeholder."""
    return "<h1>Add New Address - Coming Soon</h1><p>Add a new delivery address here.</p>"

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "message": "Monthly Organics is running"}

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    return render_template('500.html'), 500

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
        
        # Use fixed OTP for testing (will be replaced with MSG91 API later)
        otp = "290921"
        
        # Store OTP and mobile number in session
        session['otp'] = otp
        session['mobile_number'] = mobile_number
        session['otp_attempts'] = 0
        
        # For testing - print OTP to console
        print(f"OTP for {mobile_number} is: {otp} (TEST MODE)")
        
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
        
        # OTP is correct - find or create user using SQLAlchemy
        from models import User
        user = User.query.filter_by(phone=mobile_number).first()
        
        if user:
            user_id = user.id
            logging.info(f"Existing user logged in: {mobile_number}")
        else:
            # Create new user
            user = User(
                first_name=f"User",
                last_name=mobile_number[-4:],
                phone=mobile_number,
                email=f"user{mobile_number}@monthlyorganics.com"
            )
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            logging.info(f"New user created: {mobile_number}")
        
        # Login user
        session['user_id'] = user_id
        
        # Clear OTP data from session
        session.pop('otp', None)
        session.pop('mobile_number', None)
        session.pop('otp_attempts', None)
        
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
        logging.info(f"Add to cart request for variation {variation_id} by user {session.get('user_id')}")
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
        logging.info(f"Cart update request: user={user_id}, variation={variation_id}, action={action}")
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
            
            # Return empty response to remove the item from cart
            return ''
        
        # Get updated cart item details for proper display before committing
        cursor.execute("""
            SELECT 
                ci.variation_id,
                ci.quantity,
                pv.variation_name,
                pv.mrp as price,
                p.name as product_name,
                (ci.quantity * pv.mrp) as total_price
            FROM cart_items ci
            JOIN product_variations pv ON ci.variation_id = pv.id
            JOIN products p ON pv.product_id = p.id
            WHERE ci.user_id = %s AND ci.variation_id = %s
        """, (user_id, variation_id))
        
        item = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if not item:
            return "Item not found", 404
            
        # Return complete cart item HTML for cart page
        return f'''
        <div class="cart-item-wrapper border-b border-gray-100 p-4 last:border-b-0">
            <div class="flex items-start space-x-3">
                <!-- Product Image Placeholder -->
                <div class="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                </div>
                
                <!-- Product Details -->
                <div class="flex-1 min-w-0">
                    <h3 class="font-medium text-gray-900 text-sm">{item['product_name']}</h3>
                    <p class="text-sm text-gray-600">{item['variation_name']}</p>
                    
                    <div class="flex items-center justify-between mt-2">
                        <!-- Quantity Controls -->
                        <div class="flex items-center space-x-2 bg-gray-50 rounded-lg px-2 py-1">
                            <button hx-post="/update-cart/{variation_id}/decr" 
                                    hx-target="closest .cart-item-wrapper"
                                    hx-swap="outerHTML"
                                    class="w-7 h-7 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors text-sm">
                                -
                            </button>
                            <span class="px-2 font-medium text-gray-800 min-w-[24px] text-center">{item['quantity']}</span>
                            <button hx-post="/update-cart/{variation_id}/incr" 
                                    hx-target="closest .cart-item-wrapper"
                                    hx-swap="outerHTML"
                                    class="w-7 h-7 bg-green-500 text-white rounded-full flex items-center justify-center hover:bg-green-600 transition-colors text-sm">
                                +
                            </button>
                        </div>
                        
                        <!-- Price -->
                        <div class="text-right">
                            <p class="text-sm font-medium text-gray-900">₹{item['total_price']:.2f}</p>
                            <p class="text-xs text-gray-500">₹{item['price']:.2f} each</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
    except Exception as e:
        logging.error(f"Error updating cart: {e}")
        return "Error updating cart", 500

if __name__ == '__main__':
    logger.info("Starting Monthly Organics Flask application")
    logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(host='0.0.0.0', port=5000, debug=True)