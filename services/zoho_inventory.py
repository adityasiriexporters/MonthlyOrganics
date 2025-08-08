"""
Zoho Inventory API Integration Service

This module provides OAuth authentication and API interaction capabilities
for integrating with Zoho Inventory.
"""

import os
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, quote_plus
from services.database import DatabaseService

logger = logging.getLogger(__name__)

class ZohoOAuthError(Exception):
    """Custom exception for Zoho OAuth related errors"""
    pass

class ZohoAPIError(Exception):
    """Custom exception for Zoho API related errors"""
    pass

class ZohoInventoryAPI:
    """
    Zoho Inventory API client with OAuth 2.0 authentication
    """
    
    def __init__(self):
        self.client_id = os.environ.get('ZOHO_CLIENT_ID')
        self.client_secret = os.environ.get('ZOHO_CLIENT_SECRET')
        self.organization_id = os.environ.get('ZOHO_ORGANIZATION_ID')
        
        if not all([self.client_id, self.client_secret, self.organization_id]):
            raise ZohoOAuthError("Missing required Zoho credentials in environment variables")
        
        self.base_url = "https://www.zohoapis.com/inventory/v1"
        self.auth_url = "https://accounts.zoho.com/oauth/v2"
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Load existing tokens from database
        self._load_tokens()
    
    def _load_tokens(self):
        """Load OAuth tokens from database"""
        try:
            query = """
                SELECT access_token, refresh_token, expires_at 
                FROM zoho_oauth_tokens 
                WHERE service = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            result = DatabaseService.execute_query(query, ('inventory',), fetch_one=True)
            
            if result:
                self.access_token = result['access_token']
                self.refresh_token = result['refresh_token']
                self.token_expiry = result['expires_at']
                    
        except Exception as e:
            logger.warning(f"Could not load existing tokens: {e}")
    
    def _save_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """Save OAuth tokens to database"""
        try:
            expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Try to update existing token first
            update_query = """
                UPDATE zoho_oauth_tokens 
                SET access_token = %s, refresh_token = %s, expires_at = %s, updated_at = %s
                WHERE service = %s
            """
            result = DatabaseService.execute_query(update_query, (
                access_token, refresh_token, expiry_time, datetime.utcnow(), 'inventory'
            ), fetch_all=False)
            
            # If no rows were updated, insert new record
            if result == 0:
                insert_query = """
                    INSERT INTO zoho_oauth_tokens 
                    (service, access_token, refresh_token, expires_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                DatabaseService.execute_query(insert_query, (
                    'inventory', access_token, refresh_token, expiry_time, 
                    datetime.utcnow(), datetime.utcnow()
                ), fetch_all=False)
                
            self.access_token = access_token
            self.refresh_token = refresh_token
            self.token_expiry = expiry_time
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            raise ZohoOAuthError(f"Token storage failed: {e}")
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Generate OAuth authorization URL for user consent
        """
        # Use the correct scope format for Zoho Inventory API
        scope = 'ZohoInventory.FullAccess.all'
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': scope,
            'access_type': 'offline'
        }
        
        if state:
            params['state'] = state
            
        # Build URL with proper encoding
        auth_url = f"{self.auth_url}/auth?{urlencode(params)}"
        logger.info(f"Generated Zoho auth URL with scope '{params['scope']}': {auth_url}")
        return auth_url
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str):
        """
        Exchange authorization code for access and refresh tokens
        """
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        try:
            response = requests.post(f"{self.auth_url}/token", data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'error' in token_data:
                raise ZohoOAuthError(f"OAuth error: {token_data.get('error_description', token_data['error'])}")
            
            # Save tokens
            self._save_tokens(
                token_data['access_token'],
                token_data['refresh_token'],
                token_data['expires_in']
            )
            
            logger.info("Successfully obtained Zoho OAuth tokens")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise ZohoOAuthError(f"Token exchange failed: {e}")
    
    def refresh_access_token(self):
        """
        Refresh the access token using refresh token
        """
        if not self.refresh_token:
            raise ZohoOAuthError("No refresh token available")
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }
        
        try:
            response = requests.post(f"{self.auth_url}/token", data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'error' in token_data:
                raise ZohoOAuthError(f"Token refresh error: {token_data.get('error_description', token_data['error'])}")
            
            # Save new tokens
            self._save_tokens(
                token_data['access_token'],
                token_data.get('refresh_token', self.refresh_token),  # Some responses don't include new refresh token
                token_data['expires_in']
            )
            
            logger.info("Successfully refreshed Zoho access token")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh token: {e}")
            raise ZohoOAuthError(f"Token refresh failed: {e}")
    
    def _ensure_valid_token(self):
        """
        Ensure we have a valid access token, refresh if necessary
        """
        if not self.access_token:
            raise ZohoOAuthError("No access token available. Please authorize the application first.")
        
        # Check if token is expired (with 5 minute buffer)
        if self.token_expiry and datetime.utcnow() >= (self.token_expiry - timedelta(minutes=5)):
            logger.info("Access token expired, refreshing...")
            self.refresh_access_token()
    
    def _make_api_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        Make authenticated API request to Zoho Inventory
        """
        self._ensure_valid_token()
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Add organization ID to params
        if params is None:
            params = {}
        params['organization_id'] = self.organization_id
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, params=params, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, params=params, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)
            else:
                raise ZohoAPIError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle empty responses
            if not response.content:
                return {}
                
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if error_data.get('code') == 401:  # Unauthorized
                        logger.info("Token might be invalid, attempting refresh...")
                        self.refresh_access_token()
                        # Retry the request once
                        return self._make_api_request(method, endpoint, params, data)
                    raise ZohoAPIError(f"API Error: {error_data}")
                except json.JSONDecodeError:
                    raise ZohoAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
            raise ZohoAPIError(f"Request failed: {e}")
    
    # Inventory API Methods
    
    def get_items(self, page: int = 1, per_page: int = 200) -> Dict:
        """
        Get all items from Zoho Inventory
        """
        params = {
            'page': page,
            'per_page': per_page
        }
        return self._make_api_request('GET', '/items', params=params)
    
    def get_item(self, item_id: str) -> Dict:
        """
        Get a specific item from Zoho Inventory
        """
        return self._make_api_request('GET', f'/items/{item_id}')
    
    def create_item(self, item_data: Dict) -> Dict:
        """
        Create a new item in Zoho Inventory
        """
        return self._make_api_request('POST', '/items', data=item_data)
    
    def update_item(self, item_id: str, item_data: Dict) -> Dict:
        """
        Update an existing item in Zoho Inventory
        """
        return self._make_api_request('PUT', f'/items/{item_id}', data=item_data)
    
    def create_sales_order(self, order_data: Dict) -> Dict:
        """
        Create a sales order in Zoho Inventory
        """
        return self._make_api_request('POST', '/salesorders', data=order_data)
    
    def get_sales_orders(self, page: int = 1, per_page: int = 200) -> Dict:
        """
        Get sales orders from Zoho Inventory
        """
        params = {
            'page': page,
            'per_page': per_page
        }
        return self._make_api_request('GET', '/salesorders', params=params)
    
    def update_item_quantity(self, item_id: str, quantity_adjustment: Dict) -> Dict:
        """
        Update item quantity in Zoho Inventory
        """
        return self._make_api_request('POST', f'/items/{item_id}/quantityadjustment', data=quantity_adjustment)
    
    def is_authenticated(self) -> bool:
        """
        Check if we have valid authentication
        """
        try:
            self._ensure_valid_token()
            return True
        except ZohoOAuthError:
            return False