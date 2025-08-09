"""
Debug routes for Zoho integration
Provides debugging endpoints for troubleshooting Zoho API connection
"""

from flask import Blueprint, jsonify, request
from models import ZohoToken, db
import requests
import os
import logging

logger = logging.getLogger(__name__)

zoho_debug_bp = Blueprint('zoho_debug', __name__, url_prefix='/zoho')

@zoho_debug_bp.route('/debug')
def debug_connection():
    """Debug endpoint to check Zoho connection status and configuration"""
    try:
        # Check environment variables
        env_status = {
            'ZOHO_CLIENT_ID': bool(os.environ.get('ZOHO_CLIENT_ID')),
            'ZOHO_CLIENT_SECRET': bool(os.environ.get('ZOHO_CLIENT_SECRET')),
            'ZOHO_REDIRECT_URI': bool(os.environ.get('ZOHO_REDIRECT_URI')),
            'ZOHO_ORGANIZATION_ID': bool(os.environ.get('ZOHO_ORGANIZATION_ID'))
        }
        
        # Check database token
        token = ZohoToken.query.first()
        token_status = {
            'token_exists': bool(token),
            'has_access_token': bool(token and token.access_token),
            'has_refresh_token': bool(token and token.refresh_token),
            'token_expired': token.is_expired if token else None,
            'created_at': token.created_at.isoformat() if token else None,
            'updated_at': token.updated_at.isoformat() if token else None
        }
        
        # Test API connection if token exists
        api_test = None
        if token and token.access_token:
            api_test = test_zoho_api_connection(token.access_token)
        
        return jsonify({
            'status': 'debug_info',
            'environment': env_status,
            'token_info': token_status,
            'api_test': api_test,
            'message': 'Debug information collected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Debug error: {str(e)}'
        }), 500

def test_zoho_api_connection(access_token):
    """Test Zoho API connection with current token"""
    try:
        org_id = os.environ.get('ZOHO_ORGANIZATION_ID')
        if not org_id:
            return {'status': 'error', 'message': 'No organization ID configured'}
        
        # Test with Zoho API - get organization info
        headers = {
            'Authorization': f'Zoho-oauthtoken {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Use India domain for API calls
        api_url = f'https://www.zohoapis.in/inventory/v1/organizations/{org_id}'
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        return {
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'response_size': len(response.text),
            'has_org_data': 'organization' in response.text.lower(),
            'error_details': response.text if response.status_code != 200 else None
        }
        
    except Exception as e:
        return {
            'status': 'exception',
            'message': str(e)
        }