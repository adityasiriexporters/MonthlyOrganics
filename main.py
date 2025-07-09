import os
import logging
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from decimal import Decimal

# Import services and utilities
from models import db, init_db
from services.database import CartService, UserService, AddressService
from utils.decorators import login_required, validate_mobile_number, validate_otp
from utils.template_helpers import (
    render_cart_item, render_store_quantity_stepper, 
    render_add_to_cart_button, render_cart_totals
)

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
    
    # Get user addresses if logged in
    user_addresses = []
    selected_address = None
    
    if 'user_id' in session:
        try:
            user_id = session['user_id']
            user_addresses = AddressService.get_user_addresses(user_id)
            
            # Get default address or first address
            for addr in user_addresses:
                if addr['is_default']:
                    selected_address = addr
                    break
            
            # If no default, use first address
            if not selected_address and user_addresses:
                selected_address = user_addresses[0]
                
        except Exception as e:
            logger.error(f"Error loading addresses for homepage: {e}")
            user_addresses = []
            selected_address = None
    
    return render_template('index.html', 
                         user_addresses=user_addresses,
                         selected_address=selected_address)

@app.route('/profile')
def profile():
    """Profile page route."""
    try:
        return render_template('profile.html')
    except Exception as e:
        logger.error(f"Error rendering profile page: {e}")
        return render_template('profile.html')

# Import store functions from routes module
from routes.store import store as store_view, products_by_category, all_products

# Store routes 
app.add_url_rule('/store', 'store', store_view, methods=['GET'])
app.add_url_rule('/products/<int:category_id>', 'products_by_category', products_by_category, methods=['GET'])
app.add_url_rule('/all-products', 'all_products', all_products, methods=['GET'])

@app.route('/cart')
@login_required
def cart():
    """Display user's shopping cart using CartService."""
    try:
        user_id = session['user_id']
        logger.info(f"Cart page accessed by user_id: {user_id}")
        
        # Use CartService for database operations
        cart_items = CartService.get_cart_items(user_id)
        logger.info(f"Found {len(cart_items)} cart items for user {user_id}")
        
        # Calculate cart totals
        subtotal = sum(item['total_price'] for item in cart_items)
        delivery_fee = Decimal('50.00') if subtotal > 0 else Decimal('0.00')  # ₹50 delivery fee
        total = subtotal + delivery_fee
        
        return render_template('cart.html', 
                             cart_items=cart_items,
                             subtotal=subtotal,
                             delivery_fee=delivery_fee,
                             total=total)
        
    except Exception as e:
        logger.error(f"Error loading cart: {e}")
        flash('An error occurred while loading your cart. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/orders')
def orders():
    """Orders page route - placeholder."""
    return render_template('profile.html')

@app.route('/support')
def support():
    """Support page route - placeholder."""
    return render_template('profile.html')

@app.route('/wallet')
def wallet():
    """Wallet page route - placeholder."""
    return render_template('profile.html')

@app.route('/rewards')
def rewards():
    """Rewards page route - placeholder."""
    return render_template('profile.html')

@app.route('/profile-settings')
def profile_settings():
    """Profile settings page route - placeholder."""
    return render_template('profile.html')

@app.route('/addresses')
@login_required
def addresses():
    """Addresses page route."""
    try:
        user_id = session['user_id']
        
        # Get user's addresses using AddressService
        user_addresses = AddressService.get_user_addresses(user_id)
        logger.info(f"Found {len(user_addresses)} addresses for user {user_id}")
        
        return render_template('addresses.html', addresses=user_addresses)
        
    except Exception as e:
        logger.error(f"Error loading addresses: {e}")
        flash('An error occurred while loading addresses. Please try again.', 'error')
        return redirect(url_for('profile'))

@app.route('/add-address')
@login_required
def add_address():
    """Add address page route."""
    return render_template('add_address.html', 
                         google_maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))

@app.route('/save-address', methods=['POST'])
@login_required
def save_address():
    """Save new address."""
    try:
        user_id = session['user_id']
        
        # Get form data
        address_data = {
            'nickname': request.form.get('nickname', '').strip(),
            'house_number': request.form.get('house_number', '').strip(),
            'block_name': request.form.get('block_name', '').strip(),
            'floor_door': request.form.get('floor_door', '').strip(),
            'contact_number': request.form.get('contact_number', '').strip(),
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0)),
            'locality': request.form.get('locality', '').strip(),
            'city': request.form.get('city', '').strip(),
            'pincode': request.form.get('pincode', '').strip(),
            'nearby_landmark': request.form.get('nearby_landmark', '').strip(),
            'address_notes': request.form.get('address_notes', '').strip(),
            'is_default': request.form.get('is_default') == 'on'
        }
        
        # Validate required fields
        required_fields = ['nickname', 'house_number', 'floor_door', 'contact_number', 'locality', 'city', 'pincode']
        for field in required_fields:
            if not address_data[field]:
                flash(f'{field.replace("_", " ").title()} is required.', 'error')
                return redirect(url_for('add_address'))
        
        # Validate latitude and longitude
        if address_data['latitude'] == 0 or address_data['longitude'] == 0:
            flash('Please select a location on the map.', 'error')
            return redirect(url_for('add_address'))
        
        # Save address using AddressService
        address_id = AddressService.create_address(user_id, address_data)
        
        if address_id:
            flash('Address saved successfully!', 'success')
            return redirect(url_for('addresses'))
        else:
            flash('Error saving address. Please try again.', 'error')
            return redirect(url_for('add_address'))
            
    except Exception as e:
        logger.error(f"Error saving address: {e}")
        flash('An error occurred while saving the address. Please try again.', 'error')
        return redirect(url_for('add_address'))

@app.route('/set-default-address/<int:address_id>')
@login_required
def set_default_address(address_id):
    """Set an address as default."""
    try:
        user_id = session['user_id']
        
        if AddressService.set_default_address(address_id, user_id):
            flash('Default address updated successfully!', 'success')
        else:
            flash('Error updating default address.', 'error')
            
    except Exception as e:
        logger.error(f"Error setting default address: {e}")
        flash('An error occurred. Please try again.', 'error')
    
    return redirect(url_for('addresses'))

@app.route('/delete-address/<int:address_id>')
@login_required
def delete_address(address_id):
    """Delete an address."""
    try:
        user_id = session['user_id']
        
        if AddressService.delete_address(address_id, user_id):
            flash('Address deleted successfully!', 'success')
        else:
            flash('Error deleting address.', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        flash('An error occurred. Please try again.', 'error')
    
    return redirect(url_for('addresses'))

@app.route('/api/addresses')
@login_required
def api_addresses():
    """API endpoint to get user addresses for dropdown."""
    try:
        user_id = session['user_id']
        user_addresses = AddressService.get_user_addresses(user_id)
        
        # Convert to simple list for JSON response
        addresses_list = []
        for addr in user_addresses:
            addresses_list.append({
                'id': addr['id'],
                'nickname': addr['nickname'],
                'locality': addr['locality'],
                'city': addr['city'],
                'is_default': addr['is_default']
            })
        
        return {'addresses': addresses_list}
        
    except Exception as e:
        logger.error(f"Error fetching addresses API: {e}")
        return {'addresses': []}

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
        
        # Validate mobile number format using utility function
        if not validate_mobile_number(mobile_number):
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
        logger.error(f"Error sending OTP: {e}")
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
        
        # Validate OTP format using utility function
        if not validate_otp(submitted_otp):
            flash('Please enter a valid 6-digit OTP.', 'error')
            return redirect(url_for('verify'))
        
        # Verify OTP
        if submitted_otp != stored_otp:
            flash(f'Invalid OTP. You have {4 - session["otp_attempts"]} attempts remaining.', 'error')
            return redirect(url_for('verify'))
        
        # OTP is correct - find or create user using UserService
        user = UserService.find_user_by_phone(mobile_number)
        
        if user:
            user_id = user.id
            logger.info(f"Existing user logged in: {mobile_number}")
        else:
            # Create new user
            user = UserService.create_user(mobile_number)
            if not user:
                flash('Error creating user account. Please try again.', 'error')
                return redirect(url_for('login'))
            user_id = user.id
            logger.info(f"New user created: {mobile_number}")
        
        # Login user
        session['user_id'] = user_id
        
        # Clear OTP data from session
        session.pop('otp', None)
        session.pop('mobile_number', None)
        session.pop('otp_attempts', None)
        
        flash('Login successful!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
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
    """Add item to cart using CartService."""
    try:
        user_id = session['user_id']
        logger.info(f"Add to cart request for variation {variation_id} by user {user_id}")
        
        # Use CartService to add item
        new_quantity = CartService.add_to_cart(user_id, variation_id)
        
        if new_quantity is None:
            return "Error adding to cart", 500
        
        # Return quantity stepper HTML using template helper
        return render_store_quantity_stepper(variation_id, new_quantity)
        
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return "Error adding to cart", 500

@app.route('/update-cart/<int:variation_id>/<string:action>', methods=['POST'])
@login_required
def update_cart(variation_id, action):
    """Update cart item quantity using CartService and template helpers."""
    try:
        user_id = session['user_id']
        logger.info(f"Cart update request: user={user_id}, variation={variation_id}, action={action}")
        
        # Validate action
        if action not in ['incr', 'decr']:
            return "Invalid action", 400
        
        # Use CartService to update quantity
        new_quantity = CartService.update_cart_quantity(user_id, variation_id, action)
        
        if new_quantity is None:
            return "Item not found in cart", 404
        
        # If quantity becomes 0, remove the item
        if new_quantity <= 0:
            CartService.remove_cart_item(user_id, variation_id)
            
            # Check if request comes from store page to restore Add to Cart button
            referer = request.headers.get('Referer', '')
            if '/store' in referer:
                return render_add_to_cart_button(variation_id)
            else:
                # Return empty response to remove the item from cart page
                return ''
        
        # Get updated cart item details
        item = CartService.get_cart_item_details(user_id, variation_id)
        
        if not item:
            return "Item not found", 404
        
        # Check if request comes from store page (referer check)
        referer = request.headers.get('Referer', '')
        if '/store' in referer:
            # Return simple quantity stepper for store page
            return render_store_quantity_stepper(variation_id, item['quantity'])
        
        # Return complete cart item HTML for cart page using template helper
        return render_cart_item(item)
        
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        return "Error updating cart", 500

@app.route('/cart-totals')
@login_required
def cart_totals():
    """Return updated cart totals using CartService and template helpers."""
    try:
        user_id = session['user_id']
        logger.info(f"Calculating cart totals for user {user_id}")
        
        # Get cart items using CartService
        cart_items = CartService.get_cart_items(user_id)
        logger.info(f"Found {len(cart_items)} cart items")
        
        # Calculate cart totals with proper Decimal handling
        subtotal = Decimal('0.00')
        for item in cart_items:
            item_total = Decimal(str(item['total_price']))
            subtotal += item_total
            logger.debug(f"Item: {item['variation_name']}, total: {item_total}")
        
        delivery_fee = Decimal('50.00') if subtotal > 0 else Decimal('0.00')
        total = subtotal + delivery_fee
        
        logger.info(f"Calculated totals - Subtotal: {subtotal}, Delivery: {delivery_fee}, Total: {total}")
        
        # Return cart totals HTML using template helper
        return render_cart_totals(float(subtotal), float(delivery_fee), float(total))
        
    except Exception as e:
        logger.error(f"Error calculating cart totals: {e}", exc_info=True)
        return f"Error calculating totals: {str(e)}", 500

if __name__ == '__main__':
    logger.info("Starting Monthly Organics Flask application")
    logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(host='0.0.0.0', port=5000, debug=True)