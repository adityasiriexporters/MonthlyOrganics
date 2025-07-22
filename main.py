import os
import logging
import re
from datetime import timedelta
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from decimal import Decimal

# Import services and utilities
from models import db, init_db
from services.database import CartService
from services.security import SecureUserService, SecureAddressService, SecurityAuditLogger
from utils.decorators import login_required
from validators.forms import FormValidator
from utils.encryption import DataEncryption
from utils.template_helpers import (
    render_cart_item, render_store_quantity_stepper, 
    render_add_to_cart_button, render_cart_totals
)
from admin_auth import AdminAuth, admin_required

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_incremental_label(user_id: int, requested_nickname: str) -> str:
    """Generate incremental label for address nickname if it already exists."""
    try:
        # Get existing addresses for the user
        existing_addresses = SecureAddressService.get_user_addresses(user_id)
        existing_nicknames = [addr['nickname'].lower() for addr in existing_addresses]
        
        # Check if the requested nickname already exists
        if requested_nickname.lower() not in existing_nicknames:
            return requested_nickname
        
        # Find the highest number for this base nickname
        base_nickname = requested_nickname
        pattern = re.compile(rf"^{re.escape(base_nickname.lower())}(?: (\d+))?$")
        
        max_number = 0
        for nickname in existing_nicknames:
            match = pattern.match(nickname)
            if match:
                number_str = match.group(1)
                if number_str:
                    max_number = max(max_number, int(number_str))
                else:
                    max_number = max(max_number, 1)  # Original name counts as 1
        
        # Generate new incremental name
        new_number = max_number + 1
        return f"{base_nickname} {new_number}"
        
    except Exception as e:
        logger.error(f"Error generating incremental label: {e}")
        return requested_nickname

class Base(DeclarativeBase):
    pass

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure persistent sessions (30 days)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

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
        
        # Get user's addresses using SecureAddressService
        user_addresses = SecureAddressService.get_user_addresses(user_id)
        SecurityAuditLogger.log_data_access(user_id, "VIEW", "addresses")
        logger.info(f"Found {len(user_addresses)} addresses for user {user_id}")
        
        # Create response with cache control headers to prevent browser caching
        response = make_response(render_template('addresses.html', addresses=user_addresses))
        
        # Set cache control headers to prevent browser caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"Error loading addresses: {e}")
        flash('An error occurred while loading addresses. Please try again.', 'error')
        return redirect(url_for('profile'))

@app.route('/add-address')
@login_required
def add_address():
    """Add address page route."""
    # Create response with cache control headers to prevent browser caching
    response = make_response(render_template('add_address.html', 
                                           google_maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY')))
    
    # Set cache control headers to prevent browser caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/save-address', methods=['POST'])
@login_required
def save_address():
    """Save new address."""
    try:
        user_id = session['user_id']
        
        # Log all form data for debugging
        logger.info(f"Received form data: {dict(request.form)}")
        
        # Generate incremental label if nickname already exists
        requested_nickname = FormValidator.sanitize_string(request.form.get('nickname', ''))
        final_nickname = generate_incremental_label(user_id, requested_nickname)
        
        # Get form data with more robust handling
        address_data = {
            'nickname': final_nickname,
            'house_number': FormValidator.sanitize_string(request.form.get('house_number', '')),
            'block_name': FormValidator.sanitize_string(request.form.get('block_name', '')),
            'floor_door': FormValidator.sanitize_string(request.form.get('floor_door', '')),
            'contact_number': FormValidator.sanitize_string(request.form.get('contact_number', '')),
            'receiver_name': FormValidator.sanitize_string(request.form.get('receiver_name', '')),
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0)),
            'locality': FormValidator.sanitize_string(request.form.get('locality', '')),
            'city': FormValidator.sanitize_string(request.form.get('city', '')),
            'pincode': FormValidator.sanitize_string(request.form.get('pincode', '')),
            'nearby_landmark': FormValidator.sanitize_string(request.form.get('nearby_landmark', '')),
            'address_notes': FormValidator.sanitize_string(request.form.get('address_notes', '')),
            'is_default': request.form.get('is_default') == 'on'
        }
        
        logger.info(f"Processed address data: {address_data}")
        
        # Validate address data using FormValidator
        is_valid, errors = FormValidator.validate_address_data(address_data)
        logger.info(f"Validation result: valid={is_valid}, errors={errors}")
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('add_address'))
        
        # Save address using SecureAddressService
        logger.info(f"Attempting to save address for user {user_id}")
        address_id = SecureAddressService.create_address(user_id, address_data)
        logger.info(f"Address creation result: {address_id}")
        
        SecurityAuditLogger.log_data_access(user_id, "CREATE", "address", bool(address_id))
        
        if address_id:
            flash('Address saved successfully!', 'success')
            # Create redirect response with cache control headers
            response = make_response(redirect(url_for('addresses')))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            flash('Error saving address. Please try again.', 'error')
            return redirect(url_for('add_address'))
            
    except Exception as e:
        logger.error(f"Error saving address: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        flash('An error occurred while saving the address. Please try again.', 'error')
        return redirect(url_for('add_address'))

@app.route('/set-default-address/<int:address_id>', methods=['GET', 'POST'])
@login_required
def set_default_address(address_id):
    """Set an address as default."""
    try:
        user_id = session['user_id']
        
        if SecureAddressService.set_default_address(address_id, user_id):
            SecurityAuditLogger.log_data_access(user_id, "UPDATE", "address_default")
            
            # Return JSON for AJAX calls, redirect for normal calls
            if request.method == 'POST' and request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify({'success': True, 'message': 'Default address updated successfully!'})
            else:
                flash('Default address updated successfully!', 'success')
        else:
            if request.method == 'POST' and request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify({'success': False, 'message': 'Error updating default address.'})
            else:
                flash('Error updating default address.', 'error')
            
    except Exception as e:
        logger.error(f"Error setting default address: {e}")
        if request.method == 'POST' and request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})
        else:
            flash('An error occurred. Please try again.', 'error')
    
    # Create redirect response with cache control headers
    response = make_response(redirect(url_for('addresses')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/edit-address/<int:address_id>')
@login_required
def edit_address(address_id):
    """Edit address page."""
    try:
        user_id = session['user_id']
        
        # Get the specific address using SecureAddressService
        addresses = SecureAddressService.get_user_addresses(user_id)
        address = None
        
        for addr in addresses:
            if addr['id'] == address_id:
                address = addr
                break
        
        if not address:
            flash('Address not found.', 'error')
            return redirect(url_for('addresses'))
        
        SecurityAuditLogger.log_data_access(user_id, "VIEW", "address")
        
        # Create response with cache control headers to prevent browser caching
        response = make_response(render_template('edit_address.html', 
                                               address=address,
                                               google_maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY')))
        
        # Set cache control headers to prevent browser caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"Error loading edit address page: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('addresses'))

@app.route('/update-address/<int:address_id>', methods=['POST'])
@login_required
def update_address(address_id):
    """Update an existing address."""
    try:
        user_id = session['user_id']
        
        # Get form data
        form_data = request.form.to_dict()
        logger.info(f"Updating address {address_id} with data: {form_data}")
        
        # Validate required fields
        required_fields = ['house_number', 'floor_door', 'locality', 'nickname', 'receiver_name', 'contact_number']
        missing_fields = [field for field in required_fields if not form_data.get(field)]
        
        if missing_fields:
            flash(f'Please fill in all required fields: {", ".join(missing_fields)}', 'error')
            return redirect(url_for('edit_address', address_id=address_id))
        
        # Validate coordinates
        try:
            latitude = float(form_data.get('latitude', 0))
            longitude = float(form_data.get('longitude', 0))
            if latitude == 0 or longitude == 0:
                flash('Invalid location coordinates.', 'error')
                return redirect(url_for('edit_address', address_id=address_id))
        except (ValueError, TypeError):
            flash('Invalid location coordinates.', 'error')
            return redirect(url_for('edit_address', address_id=address_id))
        
        # Generate incremental label if nickname already exists (only for editing existing address)
        requested_nickname = form_data.get('nickname')
        
        # For editing, we don't need incremental naming unless they're changing to a conflicting name
        # Get existing addresses excluding current one
        existing_addresses = SecureAddressService.get_user_addresses(user_id)
        existing_nicknames = [addr['nickname'].lower() for addr in existing_addresses if addr['id'] != address_id]
        
        final_nickname = requested_nickname
        if requested_nickname.lower() in existing_nicknames:
            final_nickname = generate_incremental_label(user_id, requested_nickname)
        
        # Prepare address data
        address_data = {
            'nickname': final_nickname,
            'house_number': form_data.get('house_number'),
            'block_name': form_data.get('block_name', ''),
            'floor_door': form_data.get('floor_door'),
            'locality': form_data.get('locality'),
            'city': form_data.get('city'),
            'pincode': form_data.get('pincode'),
            'latitude': latitude,
            'longitude': longitude,
            'nearby_landmark': form_data.get('nearby_landmark', ''),
            'contact_number': form_data.get('contact_number', ''),
            'address_notes': form_data.get('address_notes', ''),
            'receiver_name': form_data.get('receiver_name', ''),
            'is_default': bool(form_data.get('is_default'))
        }
        
        # Validate address data
        is_valid, errors = FormValidator.validate_address_data(address_data)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('edit_address', address_id=address_id))
        
        # Update address using SecureAddressService
        if SecureAddressService.update_address(address_id, user_id, address_data):
            SecurityAuditLogger.log_data_access(user_id, "UPDATE", "address")
            flash('Address updated successfully!', 'success')
            # Create redirect response with cache control headers
            response = make_response(redirect(url_for('addresses')))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            flash('Error updating address.', 'error')
            return redirect(url_for('edit_address', address_id=address_id))
        
    except Exception as e:
        logger.error(f"Error updating address: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('edit_address', address_id=address_id))

@app.route('/delete-address/<int:address_id>')
@login_required
def delete_address(address_id):
    """Delete an address."""
    try:
        user_id = session['user_id']
        
        if SecureAddressService.delete_address(address_id, user_id):
            SecurityAuditLogger.log_data_access(user_id, "DELETE", "address")
            flash('Address deleted successfully!', 'success')
        else:
            flash('Error deleting address.', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        flash('An error occurred. Please try again.', 'error')
    
    # Create redirect response with cache control headers
    response = make_response(redirect(url_for('addresses')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/addresses')
@login_required
def api_addresses():
    """API endpoint to get user addresses for dropdown."""
    try:
        user_id = session['user_id']
        user_addresses = SecureAddressService.get_user_addresses(user_id)
        SecurityAuditLogger.log_data_access(user_id, "VIEW", "addresses")
        
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

@app.route('/admin/migrate-data', methods=['POST'])
def migrate_data():
    """Manual endpoint to migrate existing data to encrypted format"""
    try:
        from utils.data_migration import DataMigration
        
        # Run migration
        if DataMigration.run_full_migration():
            # Verify migration
            DataMigration.verify_migration()
            return {"status": "success", "message": "Data migration completed successfully"}
        else:
            return {"status": "error", "message": "Data migration completed with errors"}, 500
            
    except Exception as e:
        logger.error(f"Manual data migration error: {e}")
        return {"status": "error", "message": f"Migration failed: {str(e)}"}, 500

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

@app.route('/signup')
def signup():
    """New user signup page."""
    # Get pre-filled phone number from query parameter
    phone_number = request.args.get('phone', '')
    return render_template('signup.html', phone_number=phone_number)

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Generate and send OTP for mobile number verification."""
    try:
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        mobile_number = request.form.get('mobile_number', '').strip()
        is_signup = request.form.get('signup') == 'true'  # Check if this is signup
        
        # Validate mobile number format
        if not FormValidator.validate_mobile_number(mobile_number):
            flash('Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.', 'error')
            return redirect(url_for('signup' if is_signup else 'login'))
        
        # Check if this is from login page (no signup flag)
        if not is_signup:
            # Login flow - check if user exists
            user = SecureUserService.find_user_by_phone(mobile_number)
            if user:
                # User exists - send OTP and proceed to verification
                otp = "290921"
                session['otp'] = otp
                session['mobile_number'] = mobile_number
                session['first_name'] = user.get('first_name', '')
                session['last_name'] = user.get('last_name', '')
                session['otp_attempts'] = 0
                session['is_existing_user'] = True
                
                logger.info(f"OTP for existing user {mobile_number} is: {otp} (TEST MODE)")
                return redirect(url_for('verify'))
            else:
                # User doesn't exist - redirect to signup with pre-filled phone
                return redirect(url_for('signup', phone=mobile_number))
        else:
            # Signup flow - validate name fields first
            first_name_valid, first_name_error = FormValidator.validate_first_name(first_name)
            if not first_name_valid:
                flash(first_name_error, 'error')
                return redirect(url_for('signup'))
            
            last_name_valid, last_name_error = FormValidator.validate_last_name(last_name)
            if not last_name_valid:
                flash(last_name_error, 'error')
                return redirect(url_for('signup'))
            
            # Check if user already exists even in signup flow
            existing_user = SecureUserService.find_user_by_phone(mobile_number)
            if existing_user:
                # User already exists - treat as login with existing names
                otp = "290921"
                session['otp'] = otp
                session['mobile_number'] = mobile_number
                session['first_name'] = existing_user.get('first_name', '')
                session['last_name'] = existing_user.get('last_name', '')
                session['otp_attempts'] = 0
                session['is_existing_user'] = True
                
                logger.info(f"OTP for existing user {mobile_number} is: {otp} (TEST MODE)")
                return redirect(url_for('verify'))
            else:
                # Truly new user - proceed with signup
                otp = "290921"
                session['otp'] = otp
                session['mobile_number'] = mobile_number
                session['first_name'] = first_name
                session['last_name'] = last_name
                session['otp_attempts'] = 0
                session['is_existing_user'] = False
                
                logger.info(f"OTP for new user {mobile_number} is: {otp} (TEST MODE)")
                return redirect(url_for('verify'))
        
    except Exception as e:
        logger.error(f"Error sending OTP: {e}")
        flash('An error occurred. Please try again.', 'error')
        # Redirect back to appropriate form based on whether it was signup
        is_signup = request.form.get('signup') == 'true'
        return redirect(url_for('signup' if is_signup else 'login'))

@app.route('/verify')
def verify():
    """OTP verification page."""
    if 'mobile_number' not in session or 'otp' not in session:
        flash('Please start by entering your mobile number.', 'error')
        return redirect(url_for('login'))
    
    mobile_number = session.get('mobile_number')
    first_name = session.get('first_name', '')
    last_name = session.get('last_name', '')
    is_existing_user = session.get('is_existing_user', False)
    
    # Show name greeting for all users who have names (existing users and new signups)
    full_name = ''
    if first_name and last_name:
        full_name = f"{first_name} {last_name}".strip()
    
    return render_template('verify.html', 
                         mobile_number=mobile_number,
                         full_name=full_name)

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
        if not FormValidator.validate_otp(submitted_otp):
            flash('Please enter a valid 6-digit OTP.', 'error')
            return redirect(url_for('verify'))
        
        # Verify OTP
        if submitted_otp != stored_otp:
            flash(f'Invalid OTP. You have {4 - session["otp_attempts"]} attempts remaining.', 'error')
            return redirect(url_for('verify'))
        
        # Get user data from session
        first_name = session.get('first_name')
        last_name = session.get('last_name')
        
        # Check if this was an existing user login or new user signup
        is_existing_user = session.get('is_existing_user', False)
        
        if is_existing_user:
            # Existing user login - user should already exist
            user = SecureUserService.find_user_by_phone(mobile_number)
            if not user:
                flash('User account not found. Please sign up first.', 'error')
                return redirect(url_for('signup'))
            
            user_id = user['id']
            SecurityAuditLogger.log_authentication_event(
                DataEncryption.hash_for_search(mobile_number)[:8], 
                "LOGIN_EXISTING_USER"
            )
            logger.info(f"Existing user logged in")
        else:
            # New user signup - create user with provided names
            if not first_name or not last_name:
                flash('Name information missing. Please sign up again.', 'error')
                return redirect(url_for('signup'))
            
            # Check if user was already created during this session to prevent duplicates
            existing_user = SecureUserService.find_user_by_phone(mobile_number)
            if existing_user:
                # User was already created, use existing user
                user_id = existing_user['id']
                logger.info(f"User already exists, using existing account: {user_id}")
            else:
                # Create new user
                user = SecureUserService.create_user_with_details(mobile_number, first_name, last_name)
                if not user:
                    SecurityAuditLogger.log_authentication_event(
                        DataEncryption.hash_for_search(mobile_number)[:8], 
                        "USER_CREATION_FAILED", 
                        False
                    )
                    flash('Error creating user account. Please try again.', 'error')
                    return redirect(url_for('signup'))
                
                user_id = user['id']
                SecurityAuditLogger.log_authentication_event(
                    DataEncryption.hash_for_search(mobile_number)[:8], 
                    "NEW_USER_CREATED"
                )
                logger.info(f"New user created")
        
        # Login user with permanent session
        session.permanent = True  # Make session permanent (lasts 30 days)
        session['user_id'] = user_id
        
        # Clear OTP data from session
        session.pop('otp', None)
        session.pop('mobile_number', None)
        session.pop('first_name', None)
        session.pop('last_name', None)
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


# ===== CHECKOUT SECTION =====

@app.route('/pre-checkout')
@login_required
def pre_checkout():
    """Pre-checkout page for address selection and confirmation."""
    try:
        user_id = session['user_id']
        
        # Check if cart has items
        cart_items = CartService.get_cart_items(user_id)
        if not cart_items:
            flash('Your cart is empty. Please add items before checkout.', 'error')
            return redirect(url_for('cart'))
        
        # Get user's addresses
        user_addresses = SecureAddressService.get_user_addresses(user_id)
        SecurityAuditLogger.log_data_access(user_id, "VIEW", "addresses_checkout")
        
        # Check if a specific address should be selected (from query params)
        selected_address_id = request.args.get('selected_address', type=int)
        if selected_address_id:
            for addr in user_addresses:
                if addr['id'] == selected_address_id:
                    addr['is_default'] = True
                else:
                    addr['is_default'] = False
        
        # Convert addresses to JSON for JavaScript, handling datetime serialization
        import json
        from datetime import datetime
        
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError("Type %s not serializable" % type(obj))
        
        addresses_json = json.dumps(user_addresses, default=json_serial)
        
        return render_template('pre_checkout.html', 
                             addresses=user_addresses,
                             addresses_json=addresses_json,
                             google_maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))
        
    except Exception as e:
        logger.error(f"Error loading pre-checkout: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('cart'))

@app.route('/add-new-address-for-delivery')
@login_required
def add_new_address_for_delivery():
    """Add new address page specifically for delivery checkout."""
    try:
        return render_template('add_address_for_delivery.html',
                             google_maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))
    except Exception as e:
        logger.error(f"Error loading add address for delivery page: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('pre_checkout'))

@app.route('/save-address-for-delivery', methods=['POST'])
@login_required
def save_address_for_delivery():
    """Save new address and return to pre-checkout with new address selected."""
    try:
        user_id = session['user_id']
        
        # Generate incremental label if nickname already exists
        requested_nickname = FormValidator.sanitize_string(request.form.get('nickname', ''))
        final_nickname = generate_incremental_label(user_id, requested_nickname)
        
        # Get form data
        address_data = {
            'nickname': final_nickname,
            'house_number': FormValidator.sanitize_string(request.form.get('house_number', '')),
            'block_name': FormValidator.sanitize_string(request.form.get('block_name', '')),
            'floor_door': FormValidator.sanitize_string(request.form.get('floor_door', '')),
            'contact_number': FormValidator.sanitize_string(request.form.get('contact_number', '')),
            'receiver_name': FormValidator.sanitize_string(request.form.get('receiver_name', '')),
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0)),
            'locality': FormValidator.sanitize_string(request.form.get('locality', '')),
            'city': FormValidator.sanitize_string(request.form.get('city', '')),
            'pincode': FormValidator.sanitize_string(request.form.get('pincode', '')),
            'nearby_landmark': FormValidator.sanitize_string(request.form.get('nearby_landmark', '')),
            'address_notes': FormValidator.sanitize_string(request.form.get('address_notes', '')),
            'is_default': request.form.get('is_default') == 'on'
        }
        
        # Validate address data
        is_valid, errors = FormValidator.validate_address_data(address_data)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('add_new_address_for_delivery'))
        
        # Save address
        address_id = SecureAddressService.create_address(user_id, address_data)
        SecurityAuditLogger.log_data_access(user_id, "CREATE", "address_delivery", bool(address_id))
        
        if address_id:
            flash('Address saved successfully!', 'success')
            # Redirect to pre-checkout with new address selected
            return redirect(url_for('pre_checkout', selected_address=address_id))
        else:
            flash('Error saving address. Please try again.', 'error')
            return redirect(url_for('add_new_address_for_delivery'))
            
    except Exception as e:
        logger.error(f"Error saving address for delivery: {e}")
        flash('An error occurred while saving the address. Please try again.', 'error')
        return redirect(url_for('add_new_address_for_delivery'))

@app.route('/edit-address-for-delivery/<int:address_id>')
@login_required
def edit_address_for_delivery(address_id):
    """Edit address page specifically for delivery checkout."""
    try:
        user_id = session['user_id']
        
        # Get the specific address
        addresses = SecureAddressService.get_user_addresses(user_id)
        address = None
        
        for addr in addresses:
            if addr['id'] == address_id:
                address = addr
                break
        
        if not address:
            flash('Address not found.', 'error')
            return redirect(url_for('pre_checkout'))
        
        SecurityAuditLogger.log_data_access(user_id, "VIEW", "address_edit_delivery")
        
        return render_template('edit_address_for_delivery.html',
                             address=address,
                             google_maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))
        
    except Exception as e:
        logger.error(f"Error loading edit address for delivery: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('pre_checkout'))

@app.route('/update-address-for-delivery/<int:address_id>', methods=['POST'])
@login_required
def update_address_for_delivery(address_id):
    """Update address and return to pre-checkout with updated address selected."""
    try:
        user_id = session['user_id']
        action = request.form.get('action', 'update_and_use')
        
        if action == 'update_and_use':
            # Get form data
            form_data = dict(request.form)
            
            # Validate latitude and longitude
            try:
                latitude = float(form_data.get('latitude', 0))
                longitude = float(form_data.get('longitude', 0))
            except (ValueError, TypeError):
                flash('Invalid location coordinates.', 'error')
                return redirect(url_for('edit_address_for_delivery', address_id=address_id))
            
            # Generate incremental label if nickname conflicts
            requested_nickname = form_data.get('nickname', '')
            if not requested_nickname:
                flash('Nickname is required.', 'error')
                return redirect(url_for('edit_address_for_delivery', address_id=address_id))
                
            existing_addresses = SecureAddressService.get_user_addresses(user_id)
            existing_nicknames = [addr['nickname'].lower() for addr in existing_addresses if addr['id'] != address_id]
            
            final_nickname = requested_nickname
            if requested_nickname.lower() in existing_nicknames:
                final_nickname = generate_incremental_label(user_id, requested_nickname)
            
            # Prepare address data
            address_data = {
                'nickname': final_nickname,
                'house_number': form_data.get('house_number'),
                'block_name': form_data.get('block_name', ''),
                'floor_door': form_data.get('floor_door'),
                'locality': form_data.get('locality'),
                'city': form_data.get('city'),
                'pincode': form_data.get('pincode'),
                'latitude': latitude,
                'longitude': longitude,
                'nearby_landmark': form_data.get('nearby_landmark', ''),
                'contact_number': form_data.get('contact_number', ''),
                'address_notes': form_data.get('address_notes', ''),
                'receiver_name': form_data.get('receiver_name', ''),
                'is_default': bool(form_data.get('is_default'))
            }
            
            # Validate address data
            is_valid, errors = FormValidator.validate_address_data(address_data)
            if not is_valid:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('edit_address_for_delivery', address_id=address_id))
            
            # Update address
            if SecureAddressService.update_address(address_id, user_id, address_data):
                SecurityAuditLogger.log_data_access(user_id, "UPDATE", "address_delivery")
                flash('Address updated successfully!', 'success')
                return redirect(url_for('pre_checkout', selected_address=address_id))
            else:
                flash('Error updating address.', 'error')
                return redirect(url_for('edit_address_for_delivery', address_id=address_id))
        
        # If we reach here, there was an error
        flash('Invalid action.', 'error')
        return redirect(url_for('edit_address_for_delivery', address_id=address_id))
        
    except Exception as e:
        logger.error(f"Error updating address for delivery: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('edit_address_for_delivery', address_id=address_id))

@app.route('/checkout')
@login_required
def checkout():
    """Final checkout page with order summary and payment."""
    try:
        user_id = session['user_id']
        address_id = request.args.get('address_id', type=int)
        
        if not address_id:
            flash('Please select a delivery address.', 'error')
            return redirect(url_for('pre_checkout'))
        
        # Get cart items
        cart_items = CartService.get_cart_items(user_id)
        if not cart_items:
            flash('Your cart is empty.', 'error')
            return redirect(url_for('cart'))
        
        # Get selected address
        addresses = SecureAddressService.get_user_addresses(user_id)
        selected_address = None
        
        for addr in addresses:
            if addr['id'] == address_id:
                selected_address = addr
                break
        
        if not selected_address:
            flash('Selected address not found.', 'error')
            return redirect(url_for('pre_checkout'))
        
        # Calculate totals
        subtotal = sum(item['total_price'] for item in cart_items)
        delivery_fee = Decimal('50.00') if subtotal > 0 else Decimal('0.00')
        total = subtotal + delivery_fee
        
        SecurityAuditLogger.log_data_access(user_id, "VIEW", "checkout")
        
        return render_template('checkout.html',
                             cart_items=cart_items,
                             selected_address=selected_address,
                             subtotal=subtotal,
                             delivery_fee=delivery_fee,
                             total=total)
        
    except Exception as e:
        logger.error(f"Error loading checkout: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('pre_checkout'))


# ===== ADMIN SECTION =====

@app.route('/adminlogin', methods=['GET', 'POST'])
def admin_login():
    """Admin login page and authentication handler"""
    if request.method == 'GET':
        # If already logged in, redirect to dashboard
        if AdminAuth.is_admin_logged_in():
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/admin_login.html')
    
    # Handle POST - login attempt
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('Please enter both username and password.', 'error')
        return render_template('admin/admin_login.html')
    
    if AdminAuth.verify_admin_credentials(username, password):
        AdminAuth.login_admin(username)
        flash('Welcome to Monthly Organics Admin Portal!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid credentials. Please try again.', 'error')
        return render_template('admin/admin_login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    AdminAuth.logout_admin()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with overview statistics"""
    try:
        # Get dashboard statistics
        stats = get_admin_dashboard_stats()
        recent_orders = get_recent_orders(limit=5)
        
        return render_template('admin/admin_dashboard.html', 
                             stats=stats, 
                             recent_orders=recent_orders,
                             admin_user=AdminAuth.get_admin_user())
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        flash('Error loading dashboard data.', 'error')
        return render_template('admin/admin_dashboard.html', 
                             stats=get_default_stats(), 
                             recent_orders=[],
                             admin_user=AdminAuth.get_admin_user())

@app.route('/admin/customers')
@admin_required
def admin_customers():
    """Customer management page"""
    try:
        customers = get_all_customers_with_stats()
        active_customers_count = sum(1 for c in customers if c['is_active'])
        new_customers_count = get_new_customers_count()
        
        return render_template('admin/admin_customers.html',
                             customers=customers,
                             active_customers_count=active_customers_count,
                             new_customers_count=new_customers_count,
                             admin_user=AdminAuth.get_admin_user())
    except Exception as e:
        logger.error(f"Error loading customers: {str(e)}")
        flash('Error loading customer data.', 'error')
        return render_template('admin/admin_customers.html',
                             customers=[],
                             active_customers_count=0,
                             new_customers_count=0,
                             admin_user=AdminAuth.get_admin_user())

@app.route('/admin/sales')
@admin_required
def admin_sales():
    """Sales analysis page"""
    try:
        sales_stats = get_sales_statistics()
        recent_orders = get_recent_orders(limit=10)
        category_sales = get_category_sales()
        
        # Get categories for filter dropdown
        from services.database import DatabaseService
        categories = DatabaseService.execute_query("SELECT id, name FROM categories ORDER BY name", fetch_all=True)
        
        return render_template('admin/admin_sales.html',
                             sales_stats=sales_stats,
                             recent_orders=recent_orders,
                             category_sales=category_sales,
                             categories=categories or [],
                             admin_user=AdminAuth.get_admin_user())
    except Exception as e:
        logger.error(f"Error loading sales data: {str(e)}")
        flash('Error loading sales data.', 'error')
        return render_template('admin/admin_sales.html',
                             sales_stats=get_default_sales_stats(),
                             recent_orders=[],
                             category_sales=[],
                             categories=[],
                             admin_user=AdminAuth.get_admin_user())

@app.route('/admin/delivery-zones')
@admin_required
def admin_delivery_zones():
    """Delivery zone management page"""
    try:
        from models import DeliveryZone, DeliveryZoneFreeDate
        from services.database import DatabaseService
        
        # Get all delivery zones with their free dates
        zones_query = """
            SELECT dz.id, dz.name, dz.geojson, dz.created_at,
                   COUNT(df.id) as free_dates_count,
                   STRING_AGG(df.free_date::text, ', ' ORDER BY df.free_date) as upcoming_dates
            FROM delivery_zones dz
            LEFT JOIN delivery_zone_free_dates df ON dz.id = df.zone_id AND df.free_date >= CURRENT_DATE
            GROUP BY dz.id, dz.name, dz.geojson, dz.created_at
            ORDER BY dz.created_at DESC
        """
        zones_raw = DatabaseService.execute_query(zones_query, fetch_all=True) or []
        
        # Process zones to ensure proper JSON handling
        zones = []
        for zone in zones_raw:
            zone_dict = dict(zone)
            # Ensure geojson is properly handled
            if zone_dict.get('geojson'):
                try:
                    import json
                    # If geojson is already a dict, convert to string for template
                    if isinstance(zone_dict['geojson'], dict):
                        zone_dict['geojson'] = json.dumps(zone_dict['geojson'])
                    elif isinstance(zone_dict['geojson'], str):
                        # Validate it's valid JSON
                        json.loads(zone_dict['geojson'])  # This will raise an error if invalid
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Invalid GeoJSON for zone {zone_dict['id']}: {e}, setting to None")
                    zone_dict['geojson'] = None
            zones.append(zone_dict)
        
        return render_template('admin/admin_delivery_zones.html',
                             zones=zones,
                             admin_user=AdminAuth.get_admin_user())
    except Exception as e:
        logger.error(f"Error loading delivery zones: {str(e)}")
        flash('Error loading delivery zones data.', 'error')
        return render_template('admin/admin_delivery_zones.html',
                             zones=[],
                             admin_user=AdminAuth.get_admin_user())

@app.route('/admin/delivery-zones/save', methods=['POST'])
@admin_required
def admin_save_delivery_zone():
    """Save a new delivery zone"""
    try:
        from services.database import DatabaseService
        import json
        
        data = request.get_json()
        name = data.get('name', '').strip()
        geojson = data.get('geojson')
        
        if not name or not geojson:
            return jsonify({'error': 'Zone name and geometry are required'}), 400
            
        # Check if zone name already exists
        existing_zone = DatabaseService.execute_query(
            "SELECT id FROM delivery_zones WHERE name = %s", 
            (name,), 
            fetch_one=True
        )
        
        if existing_zone:
            return jsonify({'error': 'Zone name already exists'}), 400
        
        # Convert GeoJSON to PostGIS geometry
        coordinates = geojson['geometry']['coordinates'][0]  # Get polygon exterior ring
        wkt_coords = ', '.join([f"{coord[0]} {coord[1]}" for coord in coordinates])
        geometry_wkt = f"POLYGON(({wkt_coords}))"
        
        # Insert new zone
        insert_query = """
            INSERT INTO delivery_zones (name, geometry, geojson) 
            VALUES (%s, ST_GeomFromText(%s, 4326), %s)
            RETURNING id
        """
        result = DatabaseService.execute_query(
            insert_query, 
            (name, geometry_wkt, json.dumps(geojson)), 
            fetch_one=True
        )
        
        return jsonify({'success': True, 'zone_id': result['id']})
        
    except Exception as e:
        logger.error(f"Error saving delivery zone: {str(e)}")
        return jsonify({'error': 'Failed to save delivery zone'}), 500

@app.route('/admin/delivery-zones/<int:zone_id>/add-date', methods=['POST'])
@admin_required
def admin_add_zone_free_date(zone_id):
    """Add free delivery date to a zone"""
    try:
        from services.database import DatabaseService
        from datetime import datetime, date
        data = request.get_json()
        date_str = data.get('date', '').strip()
        
        if not date_str:
            return jsonify({'error': 'Date is required'}), 400
            
        # Parse and validate date
        try:
            free_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
            
        # Check if date is in the future
        if free_date <= date.today():
            return jsonify({'error': 'Date must be in the future'}), 400
        
        # Check if zone exists
        zone_exists = DatabaseService.execute_query(
            "SELECT id FROM delivery_zones WHERE id = %s", 
            (zone_id,), 
            fetch_one=True
        )
        
        if not zone_exists:
            return jsonify({'error': 'Zone not found'}), 404
        
        # Insert free date (with duplicate handling)
        try:
            insert_query = """
                INSERT INTO delivery_zone_free_dates (zone_id, free_date) 
                VALUES (%s, %s)
            """
            DatabaseService.execute_query(insert_query, (zone_id, free_date))
            return jsonify({'success': True})
            
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                return jsonify({'error': 'This date is already assigned to the zone'}), 400
            raise
        
    except Exception as e:
        logger.error(f"Error adding zone free date: {str(e)}")
        return jsonify({'error': 'Failed to add free delivery date'}), 500

@app.route('/admin/delivery-zones/<int:zone_id>/remove-date', methods=['POST'])
@admin_required
def admin_remove_zone_free_date(zone_id):
    """Remove free delivery date from a zone"""
    try:
        from services.database import DatabaseService
        data = request.get_json()
        date_str = data.get('date', '').strip()
        
        if not date_str:
            return jsonify({'error': 'Date is required'}), 400
        
        # Delete the free date
        delete_query = """
            DELETE FROM delivery_zone_free_dates 
            WHERE zone_id = %s AND free_date = %s
        """
        DatabaseService.execute_query(delete_query, (zone_id, date_str))
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error removing zone free date: {str(e)}")
        return jsonify({'error': 'Failed to remove free delivery date'}), 500

@app.route('/admin/delivery-zones/<int:zone_id>/delete', methods=['POST'])
@admin_required
def admin_delete_delivery_zone(zone_id):
    """Delete a delivery zone"""
    try:
        from services.database import DatabaseService
        
        # Delete the zone (cascade will handle free dates)
        delete_query = "DELETE FROM delivery_zones WHERE id = %s"
        DatabaseService.execute_query(delete_query, (zone_id,))
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting delivery zone: {str(e)}")
        return jsonify({'error': 'Failed to delete delivery zone'}), 500

# ===== ADMIN DATA FUNCTIONS =====

def get_admin_dashboard_stats():
    """Get statistics for admin dashboard"""
    from services.database import DatabaseService
    
    try:
        # Total customers
        customers_query = "SELECT COUNT(*) as count FROM users"
        total_customers = DatabaseService.execute_query(customers_query, fetch_one=True)['count']
        
        # Total orders
        orders_query = "SELECT COUNT(*) as count FROM orders"
        total_orders = DatabaseService.execute_query(orders_query, fetch_one=True)['count']
        
        # Monthly revenue (current month)
        monthly_revenue_query = """
            SELECT COALESCE(SUM(total_amount), 0) as revenue 
            FROM orders 
            WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        """
        monthly_revenue = DatabaseService.execute_query(monthly_revenue_query, fetch_one=True)['revenue']
        
        # Active products (using total products since is_active column doesn't exist)
        products_query = "SELECT COUNT(*) as count FROM products"
        active_products = DatabaseService.execute_query(products_query, fetch_one=True)['count']
        
        return {
            'total_customers': total_customers or 0,
            'total_orders': total_orders or 0,
            'monthly_revenue': float(monthly_revenue or 0),
            'active_products': active_products or 0
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return get_default_stats()

def get_default_stats():
    """Default stats when database query fails"""
    return {
        'total_customers': 0,
        'total_orders': 0,
        'monthly_revenue': 0.0,
        'active_products': 0
    }

def get_recent_orders(limit=5):
    """Get recent orders for admin display"""
    from services.database import DatabaseService
    
    try:
        query = """
            SELECT o.id, o.user_id, o.total_amount, o.order_status as status, o.created_at,
                   COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id, o.user_id, o.total_amount, o.order_status, o.created_at
            ORDER BY o.created_at DESC 
            LIMIT %s
        """
        orders = DatabaseService.execute_query(query, (limit,), fetch_all=True)
        return orders or []
    except Exception as e:
        logger.error(f"Error getting recent orders: {str(e)}")
        return []

def get_filtered_orders(date_from=None, date_to=None, category_filter=None, min_amount=None, limit=50):
    """Get filtered orders with comprehensive filtering and security"""
    from services.database import DatabaseService
    
    try:
        # Base query with parameterized conditions
        base_query = """
            SELECT o.id, o.user_id, o.total_amount, o.order_status as status, o.created_at,
                   COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
        """
        
        conditions = []
        params = []
        
        # Date range filter
        if date_from:
            conditions.append("o.created_at >= %s")
            params.append(date_from)
            
        if date_to:
            conditions.append("o.created_at <= %s")
            params.append(date_to + ' 23:59:59')  # Include full day
        
        # Category filter (requires joining with product tables)
        if category_filter and category_filter.isdigit():
            base_query = """
                SELECT DISTINCT o.id, o.user_id, o.total_amount, o.order_status as status, o.created_at,
                       COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN product_variations pv ON oi.variation_id = pv.id
                LEFT JOIN products p ON pv.product_id = p.id
            """
            conditions.append("p.category_id = %s")
            params.append(int(category_filter))
        
        # Minimum amount filter
        if min_amount and min_amount.replace('.', '').isdigit():
            conditions.append("o.total_amount >= %s")
            params.append(float(min_amount))
        
        # Build final query
        if conditions:
            query = base_query + " WHERE " + " AND ".join(conditions)
        else:
            query = base_query
            
        query += """
            GROUP BY o.id, o.user_id, o.total_amount, o.order_status, o.created_at
            ORDER BY o.created_at DESC 
            LIMIT %s
        """
        params.append(limit)
        
        orders = DatabaseService.execute_query(query, tuple(params), fetch_all=True)
        return orders or []
        
    except Exception as e:
        logger.error(f"Error filtering orders: {str(e)}")
        return []

def get_all_customers_with_stats():
    """Get all customers with their order statistics and addresses"""
    try:
        import psycopg2
        import psycopg2.extras
        import os
        
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get customer data with order statistics
        query = """
            SELECT u.id, u.first_name, u.last_name, u.email, u.phone, u.custom_id,
                   u.created_at, u.is_active,
                   COUNT(o.id) as order_count,
                   MAX(o.created_at) as last_order_date,
                   COALESCE(SUM(o.total_amount), 0) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id, u.first_name, u.last_name, u.email, u.phone, u.custom_id, u.created_at, u.is_active
            ORDER BY u.created_at DESC
        """
        cursor.execute(query)
        customers = cursor.fetchall()
        
        # Process each customer and add their addresses
        result = []
        for customer in customers:
            customer_dict = dict(customer)
            
            # Get addresses for this customer
            addr_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            addr_cursor.execute("""
                SELECT id, nickname, locality, city, pincode, is_default
                FROM addresses 
                WHERE user_id = %s 
                ORDER BY is_default DESC, created_at DESC
            """, (customer_dict['id'],))
            addresses = addr_cursor.fetchall()
            
            # Convert addresses to proper format
            customer_dict['addresses'] = []
            for addr in addresses:
                customer_dict['addresses'].append({
                    'id': addr['id'],
                    'nickname': addr['nickname'] or 'Address',
                    'area': f"{addr['locality'] or ''}, {addr['city'] or ''}".strip(', '),
                    'pincode': addr['pincode'] or '',
                    'is_default': addr['is_default']
                })
            
            customer_dict['address_count'] = len(customer_dict['addresses'])
            addr_cursor.close()
            result.append(customer_dict)
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Error getting customers with addresses: {str(e)}")
        return []

def get_filtered_customers(search=None, date_from=None, date_to=None, status_filter=None, min_orders=None):
    """Get filtered customers with comprehensive filtering"""
    try:
        # Use direct database connection instead of service layer temporarily
        import psycopg2
        import psycopg2.extras
        import os
        
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Base query with parameterized conditions
        base_query = """
            SELECT u.id, u.first_name, u.last_name, u.email, u.phone, u.custom_id,
                   u.created_at, u.is_active,
                   COUNT(o.id) as order_count,
                   MAX(o.created_at) as last_order_date,
                   COALESCE(SUM(o.total_amount), 0) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            WHERE 1=1
        """
        
        conditions = []
        params = []
        
        # Search filter (name or email)
        if search and search.strip():
            conditions.append("(LOWER(u.first_name) LIKE LOWER(%s) OR LOWER(u.last_name) LIKE LOWER(%s) OR LOWER(u.email) LIKE LOWER(%s))")
            search_param = f"%{search.strip()}%"
            params.extend([search_param, search_param, search_param])
        
        # Date range filter
        if date_from:
            conditions.append("u.created_at >= %s")
            params.append(date_from)
            
        if date_to:
            conditions.append("u.created_at <= %s")
            params.append(date_to + ' 23:59:59')
        
        # Status filter
        if status_filter == 'active':
            conditions.append("u.is_active = true")
        elif status_filter == 'inactive':
            conditions.append("u.is_active = false")
        
        # Build final query
        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query
            
        query += """
            GROUP BY u.id, u.first_name, u.last_name, u.email, u.phone, u.custom_id, u.created_at, u.is_active
        """
        
        # Minimum orders filter (applied after GROUP BY)
        if min_orders and min_orders.isdigit():
            query += " HAVING COUNT(o.id) >= %s"
            params.append(int(min_orders))
            
        query += " ORDER BY u.created_at DESC"
        
        cursor.execute(query, tuple(params))
        customers = cursor.fetchall()
        
        # Process each customer and add their addresses
        result = []
        for customer in customers:
            customer_dict = dict(customer)
            
            # Get addresses for this customer
            addr_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            addr_cursor.execute("""
                SELECT id, nickname, locality, city, pincode, is_default
                FROM addresses 
                WHERE user_id = %s 
                ORDER BY is_default DESC, created_at DESC
            """, (customer_dict['id'],))
            addresses = addr_cursor.fetchall()
            
            # Convert addresses to proper format
            customer_dict['addresses'] = []
            for addr in addresses:
                customer_dict['addresses'].append({
                    'id': addr['id'],
                    'nickname': addr['nickname'] or 'Address',
                    'area': f"{addr['locality'] or ''}, {addr['city'] or ''}".strip(', '),
                    'pincode': addr['pincode'] or '',
                    'is_default': addr['is_default']
                })
            
            customer_dict['address_count'] = len(customer_dict['addresses'])
            addr_cursor.close()
            result.append(customer_dict)
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Error filtering customers: {str(e)}")
        return []

def get_new_customers_count():
    """Get count of customers who joined this month"""
    from services.database import DatabaseService
    
    try:
        query = """
            SELECT COUNT(*) as count 
            FROM users 
            WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        """
        result = DatabaseService.execute_query(query, fetch_one=True)
        return result['count'] if result else 0
    except Exception as e:
        logger.error(f"Error getting new customers count: {str(e)}")
        return 0

def get_sales_statistics():
    """Get comprehensive sales statistics"""
    from services.database import DatabaseService
    
    try:
        # Total revenue
        total_revenue_query = "SELECT COALESCE(SUM(total_amount), 0) as revenue FROM orders"
        total_revenue = DatabaseService.execute_query(total_revenue_query, fetch_one=True)['revenue']
        
        # Total orders
        total_orders_query = "SELECT COUNT(*) as count FROM orders"
        total_orders = DatabaseService.execute_query(total_orders_query, fetch_one=True)['count']
        
        # Average order value
        avg_order_query = "SELECT COALESCE(AVG(total_amount), 0) as avg_value FROM orders"
        avg_order_value = DatabaseService.execute_query(avg_order_query, fetch_one=True)['avg_value']
        
        # Monthly revenue
        monthly_revenue_query = """
            SELECT COALESCE(SUM(total_amount), 0) as revenue 
            FROM orders 
            WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        """
        monthly_revenue = DatabaseService.execute_query(monthly_revenue_query, fetch_one=True)['revenue']
        
        return {
            'total_revenue': float(total_revenue or 0),
            'total_orders': total_orders or 0,
            'average_order_value': float(avg_order_value or 0),
            'monthly_revenue': float(monthly_revenue or 0)
        }
    except Exception as e:
        logger.error(f"Error getting sales statistics: {str(e)}")
        return get_default_sales_stats()

def get_default_sales_stats():
    """Default sales stats when database query fails"""
    return {
        'total_revenue': 0.0,
        'total_orders': 0,
        'average_order_value': 0.0,
        'monthly_revenue': 0.0
    }

def get_category_sales():
    """Get sales breakdown by category"""
    from services.database import DatabaseService
    
    try:
        query = """
            SELECT c.name, COALESCE(SUM(oi.price_at_purchase * oi.quantity), 0) as revenue
            FROM categories c
            LEFT JOIN products p ON c.id = p.category_id
            LEFT JOIN product_variations pv ON p.id = pv.product_id
            LEFT JOIN order_items oi ON pv.id = oi.variation_id
            GROUP BY c.id, c.name
            HAVING SUM(oi.price_at_purchase * oi.quantity) > 0
            ORDER BY revenue DESC
        """
        categories = DatabaseService.execute_query(query, fetch_all=True)
        return categories or []
    except Exception as e:
        logger.error(f"Error getting category sales: {str(e)}")
        return []

# ===== ADMIN FILTERING AND EXPORT ROUTES =====

@app.route('/admin/customers/filter', methods=['GET'])
@admin_required
def admin_customers_filter():
    """AJAX endpoint for filtering customers"""
    try:
        # Get filter parameters with sanitization
        search = request.args.get('search', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        status_filter = request.args.get('status_filter', '').strip()
        min_orders = request.args.get('min_orders', '').strip()
        
        # Get filtered customers
        customers = get_filtered_customers(search, date_from, date_to, status_filter, min_orders)
        
        # Render table HTML
        table_html = render_template('admin/partials/customer_table.html', customers=customers)
        
        return jsonify({
            'html': table_html,
            'count': len(customers)
        })
        
    except Exception as e:
        logger.error(f"Error filtering customers: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/customers/export', methods=['GET'])
@admin_required
def admin_customers_export():
    """Export filtered customers to CSV"""
    try:
        # Get filter parameters with sanitization
        search = request.args.get('search', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        status_filter = request.args.get('status_filter', '').strip()
        min_orders = request.args.get('min_orders', '').strip()
        
        # Get filtered customers
        customers = get_filtered_customers(search, date_from, date_to, status_filter, min_orders)
        
        # Generate CSV content
        import csv
        import io
        from flask import make_response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV headers
        writer.writerow([
            'Customer ID', 'First Name', 'Last Name', 'Email', 'Phone',
            'Joined Date', 'Status', 'Order Count', 'Last Order Date', 'Total Spent'
        ])
        
        # CSV data
        for customer in customers:
            writer.writerow([
                customer['id'],
                customer['first_name'] or '',
                customer['last_name'] or '',
                customer['email'] or '',
                customer['phone'] or '',
                customer['created_at'].strftime('%Y-%m-%d') if customer['created_at'] else '',
                'Active' if customer['is_active'] else 'Inactive',
                customer['order_count'] or 0,
                customer['last_order_date'].strftime('%Y-%m-%d') if customer['last_order_date'] else 'No orders',
                f"₹{customer['total_spent'] or 0:.2f}"
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=customers_export.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting customers: {str(e)}")
        flash('Error exporting customer data.', 'error')
        return redirect(url_for('admin_customers'))

@app.route('/admin/sales/filter', methods=['GET'])
@admin_required
def admin_sales_filter():
    """AJAX endpoint for filtering sales data"""
    try:
        # Get filter parameters with sanitization
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        category_filter = request.args.get('category_filter', '').strip()
        min_amount = request.args.get('min_amount', '').strip()
        
        # Get filtered orders
        filtered_orders = get_filtered_orders(date_from, date_to, category_filter, min_amount, limit=50)
        
        # Calculate filtered statistics
        filtered_stats = get_filtered_sales_statistics(date_from, date_to, category_filter, min_amount)
        
        # Render table HTML
        orders_html = render_template('admin/partials/orders_table.html', recent_orders=filtered_orders)
        
        return jsonify({
            'orders_html': orders_html,
            'orders_count': len(filtered_orders),
            'stats': filtered_stats
        })
        
    except Exception as e:
        logger.error(f"Error filtering sales: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/sales/export', methods=['GET'])
@admin_required
def admin_sales_export():
    """Export filtered sales data to CSV"""
    try:
        # Get filter parameters with sanitization
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        category_filter = request.args.get('category_filter', '').strip()
        min_amount = request.args.get('min_amount', '').strip()
        
        # Get filtered orders (without limit for export)
        orders = get_filtered_orders(date_from, date_to, category_filter, min_amount, limit=10000)
        
        # Generate CSV content
        import csv
        import io
        from flask import make_response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV headers
        writer.writerow([
            'Order ID', 'Customer ID', 'Order Date', 'Status', 
            'Item Count', 'Total Amount'
        ])
        
        # CSV data
        for order in orders:
            writer.writerow([
                order['id'],
                order['user_id'],
                order['created_at'].strftime('%Y-%m-%d %H:%M:%S') if order['created_at'] else '',
                order['status'] or '',
                order['item_count'] or 0,
                f"₹{order['total_amount'] or 0:.2f}"
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=sales_export.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting sales data: {str(e)}")
        flash('Error exporting sales data.', 'error')
        return redirect(url_for('admin_sales'))

def get_filtered_sales_statistics(date_from=None, date_to=None, category_filter=None, min_amount=None):
    """Get sales statistics for filtered data"""
    from services.database import DatabaseService
    
    try:
        # Base query with parameterized conditions
        base_query = "SELECT COALESCE(SUM(o.total_amount), 0) as revenue, COUNT(o.id) as order_count FROM orders o"
        
        conditions = []
        params = []
        
        # Date range filter
        if date_from:
            conditions.append("o.created_at >= %s")
            params.append(date_from)
            
        if date_to:
            conditions.append("o.created_at <= %s")
            params.append(date_to + ' 23:59:59')
        
        # Category filter
        if category_filter and category_filter.isdigit():
            base_query = """
                SELECT COALESCE(SUM(o.total_amount), 0) as revenue, COUNT(DISTINCT o.id) as order_count 
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN product_variations pv ON oi.variation_id = pv.id
                JOIN products p ON pv.product_id = p.id
            """
            conditions.append("p.category_id = %s")
            params.append(int(category_filter))
        
        # Minimum amount filter
        if min_amount and min_amount.replace('.', '').isdigit():
            conditions.append("o.total_amount >= %s")
            params.append(float(min_amount))
        
        # Build final query
        if conditions:
            query = base_query + " WHERE " + " AND ".join(conditions)
        else:
            query = base_query
        
        result = DatabaseService.execute_query(query, tuple(params), fetch_one=True)
        
        # Get total stats for comparison
        total_stats = get_sales_statistics()
        
        filtered_revenue = float(result['revenue'] or 0)
        filtered_orders = result['order_count'] or 0
        avg_order = (filtered_revenue / filtered_orders) if filtered_orders > 0 else 0
        
        return {
            'total_revenue': total_stats['total_revenue'],
            'total_orders': total_stats['total_orders'], 
            'average_order_value': avg_order,
            'filtered_revenue': filtered_revenue
        }
        
    except Exception as e:
        logger.error(f"Error getting filtered sales statistics: {str(e)}")
        return get_default_sales_stats()

@app.route('/admin/delivery-zones/cleanup', methods=['POST'])
@admin_required
def admin_cleanup_delivery_dates():
    """Manual trigger for delivery date cleanup (for testing)"""
    try:
        from services.delivery_zone_scheduler import DeliveryZoneScheduler
        
        result = DeliveryZoneScheduler.cleanup_expired_free_dates()
        
        if result['status'] == 'success':
            flash(f"Cleanup completed successfully: {result['message']}", 'success')
        else:
            flash(f"Cleanup failed: {result['message']}", 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in manual cleanup: {str(e)}")
        return jsonify({'error': 'Failed to run cleanup'}), 500

@app.route('/admin/delivery-zones/stats', methods=['GET'])
@admin_required
def admin_delivery_zone_stats():
    """Get delivery zone statistics"""
    try:
        from services.delivery_zone_scheduler import DeliveryZoneScheduler
        
        stats = DeliveryZoneScheduler.get_zone_statistics()
        upcoming_dates = DeliveryZoneScheduler.get_upcoming_free_dates(days_ahead=7)
        
        return jsonify({
            'statistics': stats,
            'upcoming_dates': upcoming_dates
        })
        
    except Exception as e:
        logger.error(f"Error getting delivery zone stats: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500

# ===== SCHEDULED TASKS =====

def setup_scheduled_tasks():
    """Setup scheduled tasks for the application"""
    import threading
    import time
    from services.delivery_zone_scheduler import run_daily_cleanup
    
    def daily_scheduler():
        """Run daily tasks at 11 AM"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check if it's 11 AM (or close to it)
                if current_time.hour == 11 and current_time.minute < 5:
                    logger.info("Running daily scheduled tasks")
                    
                    # Run delivery zone cleanup
                    cleanup_result = run_daily_cleanup()
                    logger.info(f"Daily cleanup result: {cleanup_result}")
                    
                    # Sleep for 1 hour to avoid running multiple times
                    time.sleep(3600)
                
                # Check every 5 minutes
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in daily scheduler: {str(e)}")
                time.sleep(3600)  # Sleep for 1 hour on error
    
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Daily scheduler started successfully")

if __name__ == '__main__':
    logger.info("Starting Monthly Organics Flask application")
    logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Setup scheduled tasks
    setup_scheduled_tasks()
    
    app.run(host='0.0.0.0', port=5000, debug=True)