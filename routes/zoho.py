"""
Zoho Inventory API integration module for OAuth2 authentication and API calls.
"""
import os
import logging
import requests
from urllib.parse import urlencode
from flask import Blueprint, request, redirect, url_for, session, flash, jsonify
from models import db

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint
zoho_bp = Blueprint('zoho', __name__, url_prefix='/zoho')

# Zoho API configuration (India domain)
ZOHO_BASE_URL = "https://accounts.zoho.in"
ZOHO_API_BASE_URL = "https://inventory.zoho.in/api/v1"

# Get configuration from environment
CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID')
CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('ZOHO_REDIRECT_URI')
ORGANIZATION_ID = os.environ.get('ZOHO_ORGANIZATION_ID')

# Define scopes for Zoho Inventory API
SCOPES = [
    'ZohoInventory.items.ALL',
    'ZohoInventory.salesorders.ALL',
    'ZohoInventory.invoices.ALL',
    'ZohoInventory.contacts.ALL',
    'ZohoInventory.settings.READ'
]

@zoho_bp.route('/authorize')
def authorize():
    """
    Construct Zoho authorization URL and redirect user to it.
    This initiates the OAuth2 flow.
    """
    try:
        # Validate configuration
        if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
            flash('Zoho configuration is incomplete. Please check environment variables.', 'error')
            return redirect(url_for('index'))
        
        # Build authorization URL parameters
        # Generate state parameter for security
        import uuid
        state = str(uuid.uuid4())
        session['oauth_state'] = state
        
        auth_params = {
            'scope': ','.join(SCOPES),
            'client_id': CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': REDIRECT_URI,
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        
        # Construct the full authorization URL
        auth_url = f"{ZOHO_BASE_URL}/oauth/v2/auth?{urlencode(auth_params)}"
        
        logger.info(f"Redirecting to Zoho authorization URL: {auth_url}")
        
        # Redirect user to Zoho authorization page
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error constructing Zoho authorization URL: {e}")
        flash('Failed to initiate Zoho authorization', 'error')
        return redirect(url_for('index'))

@zoho_bp.route('/callback')
def callback():
    """
    Handle the callback from Zoho after user authorization.
    Exchange authorization code for access_token and refresh_token.
    """
    try:
        logger.info(f"Zoho callback received with args: {request.args}")
        
        # Get authorization code from query parameters
        auth_code = request.args.get('code')
        error = request.args.get('error')
        state = request.args.get('state')
        
        if error:
            logger.error(f"Zoho authorization error: {error}")
            flash(f'Zoho authorization failed: {error}', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if not auth_code:
            logger.error("No authorization code received from Zoho")
            flash('No authorization code received from Zoho', 'error')
            return redirect(url_for('admin_dashboard'))
            
        # Validate state parameter (optional but recommended for security)
        expected_state = session.get('oauth_state')
        if expected_state and state != expected_state:
            logger.warning(f"OAuth state mismatch. Expected: {expected_state}, Got: {state}")
            # Continue anyway for now, but log the issue
        
        # Clear the state from session
        session.pop('oauth_state', None)
        
        logger.info(f"Processing authorization code: {auth_code[:20]}...")
        
        # Add timing information for debugging
        import time
        callback_time = time.time()
        logger.info(f"Callback received at timestamp: {callback_time}")
        
        # Exchange authorization code for tokens immediately
        token_data = exchange_code_for_tokens(auth_code)
        
        if token_data and token_data.get('access_token'):
            # Store tokens securely
            store_result = store_zoho_tokens(token_data)
            
            if store_result:
                flash('Successfully connected to Zoho Inventory!', 'success')
                logger.info("Zoho authorization completed successfully")
            else:
                flash('Connected to Zoho but failed to store tokens. Please try again.', 'warning')
                logger.warning("Token exchange successful but storage failed")
            
            # Redirect to admin dashboard
            return redirect(url_for('admin_dashboard'))
        else:
            logger.error("Token exchange failed - no valid access token received")
            flash('Failed to exchange authorization code for tokens. The authorization code may have expired.', 'error')
            return redirect(url_for('admin_dashboard'))
            
    except Exception as e:
        logger.error(f"Error in Zoho callback: {e}")
        flash('Error processing Zoho authorization callback', 'error')
        return redirect(url_for('admin_dashboard'))

def exchange_code_for_tokens(auth_code):
    """
    Exchange authorization code for access_token and refresh_token.
    
    Args:
        auth_code (str): Authorization code from Zoho
        
    Returns:
        dict: Token data including access_token, refresh_token, expires_in
    """
    try:
        token_url = f"{ZOHO_BASE_URL}/oauth/v2/token"
        
        token_params = {
            'grant_type': 'authorization_code',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'code': auth_code
        }
        
        logger.info(f"Exchanging authorization code for tokens. URL: {token_url}")
        logger.info(f"Token params (without sensitive data): grant_type={token_params['grant_type']}, redirect_uri={token_params['redirect_uri']}")
        
        response = requests.post(token_url, data=token_params)
        
        logger.info(f"Token exchange response status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info(f"Token response keys: {list(token_data.keys())}")
            
            # Check if response contains error even with 200 status
            if 'error' in token_data:
                logger.error(f"Zoho returned error in token response: {token_data.get('error')} - {token_data.get('error_description', 'No description')}")
                return None
            
            # Validate required token fields
            if not token_data.get('access_token'):
                logger.error("No access_token in response")
                return None
                
            logger.info(f"Successfully received valid tokens from Zoho")
            logger.info(f"Token type: {token_data.get('token_type')}, expires_in: {token_data.get('expires_in')}")
            return token_data
        else:
            logger.error(f"Token exchange failed. Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception during token exchange: {e}")
        return None

def store_zoho_tokens(token_data):
    """
    Store Zoho tokens in the database.
    
    Args:
        token_data (dict): Token data from Zoho
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from models import ZohoToken
        
        # Validate token data before storing
        if not token_data.get('access_token'):
            logger.error("Cannot store tokens - no access_token provided")
            return False
        
        # Check if token record already exists
        existing_token = ZohoToken.query.first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = token_data.get('access_token')
            existing_token.refresh_token = token_data.get('refresh_token')
            existing_token.expires_in = token_data.get('expires_in')
            existing_token.token_type = token_data.get('token_type', 'Bearer')
            logger.info("Updating existing Zoho token")
        else:
            # Create new token record
            new_token = ZohoToken(
                access_token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                expires_in=token_data.get('expires_in'),
                token_type=token_data.get('token_type', 'Bearer')
            )
            db.session.add(new_token)
            logger.info("Creating new Zoho token")
        
        db.session.commit()
        logger.info("Zoho tokens stored successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error storing Zoho tokens: {e}")
        db.session.rollback()
        return False

@zoho_bp.route('/status')
def connection_status():
    """
    Check the current Zoho connection status.
    """
    try:
        from models import ZohoToken
        
        token = ZohoToken.query.first()
        
        if token and token.access_token:
            # Test the connection by making a simple API call
            if test_zoho_connection(token.access_token):
                return jsonify({
                    'status': 'connected',
                    'message': 'Zoho Inventory connection is active'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Zoho token exists but connection test failed'
                })
        else:
            return jsonify({
                'status': 'not_connected',
                'message': 'No Zoho authorization found'
            })
            
    except Exception as e:
        logger.error(f"Error checking Zoho status: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error checking connection status'
        })

def test_zoho_connection(access_token):
    """
    Test Zoho API connection by making a simple API call.
    
    Args:
        access_token (str): Zoho access token
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        headers = {
            'Authorization': f'Zoho-oauthtoken {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Make a simple API call to get organization info using India domain
        url = f"https://www.zohoapis.in/inventory/v1/organizations/{ORGANIZATION_ID}"
        response = requests.get(url, headers=headers, timeout=10)
        
        logger.info(f"Zoho API test: {response.status_code} - {response.text[:200]}")
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error testing Zoho connection: {e}")
        return False

@zoho_bp.route('/refresh-token')
def refresh_token():
    """
    Refresh expired Zoho access token using refresh token.
    """
    try:
        from models import ZohoToken
        
        token = ZohoToken.query.first()
        if not token or not token.refresh_token:
            return jsonify({
                'status': 'error',
                'message': 'No refresh token available. Please re-authorize.'
            }), 400
        
        # Prepare refresh token request
        refresh_url = f"{ZOHO_BASE_URL}/oauth/v2/token"
        refresh_params = {
            'grant_type': 'refresh_token',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'refresh_token': token.refresh_token
        }
        
        logger.info("Attempting to refresh Zoho access token")
        response = requests.post(refresh_url, data=refresh_params)
        
        if response.status_code == 200:
            token_data = response.json()
            
            if 'error' in token_data:
                logger.error(f"Token refresh error: {token_data.get('error')}")
                return jsonify({
                    'status': 'error',
                    'message': 'Token refresh failed. Please re-authorize.'
                }), 400
            
            # Update token in database
            token.access_token = token_data.get('access_token')
            # Some refresh responses don't include new refresh token
            if token_data.get('refresh_token'):
                token.refresh_token = token_data.get('refresh_token')
            if token_data.get('expires_in'):
                token.expires_in = token_data.get('expires_in')
            
            db.session.commit()
            logger.info("Access token refreshed successfully")
            
            return jsonify({
                'status': 'success',
                'message': 'Token refreshed successfully'
            })
        else:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to refresh token. Please re-authorize.'
            }), 400
            
    except Exception as e:
        logger.error(f"Exception during token refresh: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error refreshing token'
        }), 500

@zoho_bp.route('/clear-tokens', methods=['POST'])
def clear_tokens():
    """
    Clear stored Zoho tokens (for testing/debugging).
    """
    try:
        from models import ZohoToken
        
        # Delete all tokens
        ZohoToken.query.delete()
        db.session.commit()
        
        logger.info("All Zoho tokens cleared")
        return jsonify({
            'status': 'success',
            'message': 'All tokens cleared successfully'
        })
        
    except Exception as e:
        logger.error(f"Error clearing tokens: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error clearing tokens'
        }), 500