"""
Address management blueprint for Monthly Organics
Handles all address-related routes with Google Maps integration
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from services.address_service import AddressService
from utils.decorators import login_required
from config import Config

logger = logging.getLogger(__name__)

addresses_bp = Blueprint('addresses', __name__)


@addresses_bp.route('/addresses')
@login_required
def addresses():
    """Saved addresses page with encrypted address management."""
    try:
        user_id = session['user_id']
        user_addresses = AddressService.get_user_addresses(user_id)
        
        return render_template('addresses/addresses.html', addresses=user_addresses)
        
    except Exception as e:
        logger.error(f"Error loading addresses: {e}")
        flash('Error loading addresses', 'error')
        return redirect(url_for('main.profile'))


@addresses_bp.route('/add-address')
@login_required
def add_address():
    """Add new address page with Google Maps integration."""
    try:
        google_maps_api_key = Config.GOOGLE_MAPS_API_KEY
        if not google_maps_api_key:
            flash('Google Maps is currently unavailable', 'error')
            return redirect(url_for('addresses.addresses'))
        
        return render_template('addresses/add_address.html', 
                             google_maps_api_key=google_maps_api_key)
        
    except Exception as e:
        logger.error(f"Error loading add address page: {e}")
        flash('Error loading add address page', 'error')
        return redirect(url_for('addresses.addresses'))


@addresses_bp.route('/save-address', methods=['POST'])
@login_required
def save_address():
    """Save new address with encryption."""
    try:
        user_id = session['user_id']
        address_data = request.get_json()
        
        # Validate required fields
        validation_error = _validate_address_data(address_data)
        if validation_error:
            return validation_error, 400
        
        address_id = AddressService.save_address(user_id, address_data)
        
        if address_id:
            flash('Address saved successfully!', 'success')
            return '', 200
        else:
            return 'Failed to save address', 500
            
    except Exception as e:
        logger.error(f"Error saving address: {e}")
        return f'Error saving address: {str(e)}', 500


@addresses_bp.route('/edit-address/<int:address_id>')
@login_required
def edit_address(address_id):
    """Edit address page with Google Maps integration."""
    try:
        user_id = session['user_id']
        address = AddressService.get_address_by_id(user_id, address_id)
        
        if not address:
            flash('Address not found', 'error')
            return redirect(url_for('addresses.addresses'))
        
        google_maps_api_key = Config.GOOGLE_MAPS_API_KEY
        if not google_maps_api_key:
            flash('Google Maps is currently unavailable', 'error')
            return redirect(url_for('addresses.addresses'))
        
        return render_template('addresses/edit_address.html', 
                             address=address, 
                             google_maps_api_key=google_maps_api_key)
        
    except Exception as e:
        logger.error(f"Error loading edit address page: {e}")
        flash('Error loading edit address page', 'error')
        return redirect(url_for('addresses.addresses'))


@addresses_bp.route('/update-address/<int:address_id>', methods=['POST'])
@login_required
def update_address(address_id):
    """Update existing address with encryption."""
    try:
        user_id = session['user_id']
        address_data = request.get_json()
        
        # Validate required fields
        validation_error = _validate_address_data(address_data)
        if validation_error:
            return validation_error, 400
        
        success = AddressService.update_address(user_id, address_id, address_data)
        
        if success:
            flash('Address updated successfully!', 'success')
            return '', 200
        else:
            return 'Failed to update address', 500
            
    except Exception as e:
        logger.error(f"Error updating address: {e}")
        return f'Error updating address: {str(e)}', 500


@addresses_bp.route('/set-default-address/<int:address_id>', methods=['POST'])
@login_required
def set_default_address(address_id):
    """Set an address as default."""
    try:
        user_id = session['user_id']
        success = AddressService.set_default_address(user_id, address_id)
        
        if success:
            flash('Default address updated', 'success')
            address = AddressService.get_address_by_id(user_id, address_id)
            if address:
                return render_template('addresses/partials/address_card.html', address=address)
        
        return 'Failed to set default address', 500
        
    except Exception as e:
        logger.error(f"Error setting default address: {e}")
        return f'Error setting default address: {str(e)}', 500


@addresses_bp.route('/delete-address/<int:address_id>', methods=['DELETE'])
@login_required
def delete_address(address_id):
    """Delete an address."""
    try:
        user_id = session['user_id']
        
        # Check if it's the default address
        address = AddressService.get_address_by_id(user_id, address_id)
        if address and address['is_default']:
            return 'Cannot delete default address', 400
        
        success = AddressService.delete_address(user_id, address_id)
        
        if success:
            flash('Address deleted successfully', 'success')
            return '', 200
        else:
            return 'Failed to delete address', 500
            
    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        return f'Error deleting address: {str(e)}', 500


def _validate_address_data(address_data):
    """Validate address data and return error message if invalid."""
    required_fields = [
        'house_no', 'floor_door', 'address_label', 
        'receiver_name', 'receiver_phone', 'latitude', 'longitude'
    ]
    
    for field in required_fields:
        if not address_data.get(field):
            return f"Missing required field: {field}"
    
    return None