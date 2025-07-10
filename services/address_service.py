"""
Address service for Monthly Organics
Handles secure address storage with encryption and Google Maps integration
"""
import json
import logging
from typing import List, Dict, Optional
from cryptography.fernet import Fernet
import os
import base64
from services.database import DatabaseService

logger = logging.getLogger(__name__)

class AddressService:
    """Service for secure address operations with encryption"""
    
    @staticmethod
    def _get_encryption_key() -> bytes:
        """Get or create encryption key for address data"""
        # Use session secret as base for encryption key
        session_secret = os.environ.get('SESSION_SECRET', 'default-key-for-development')
        # Create a 32-byte key from session secret
        key = base64.urlsafe_b64encode(session_secret.encode()[:32].ljust(32, b'0'))
        return key
    
    @staticmethod
    def _encrypt_address_data(address_data: dict) -> str:
        """Encrypt sensitive address information"""
        try:
            key = AddressService._get_encryption_key()
            fernet = Fernet(key)
            
            # Convert address data to JSON and encrypt
            json_data = json.dumps(address_data)
            encrypted_data = fernet.encrypt(json_data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Error encrypting address data: {e}")
            raise
    
    @staticmethod
    def _decrypt_address_data(encrypted_data: str) -> dict:
        """Decrypt address information"""
        try:
            key = AddressService._get_encryption_key()
            fernet = Fernet(key)
            
            # Decrypt and convert back to dict
            decrypted_data = fernet.decrypt(encrypted_data.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Error decrypting address data: {e}")
            return {}
    
    @staticmethod
    def save_address(user_id: int, address_data: dict) -> Optional[int]:
        """Save a new address with encryption"""
        try:
            # Extract non-sensitive data
            address_label = address_data.get('address_label', '')
            latitude = address_data.get('latitude')
            longitude = address_data.get('longitude')
            is_default = address_data.get('is_default', False)
            
            # Prepare sensitive data for encryption
            sensitive_data = {
                'house_no': address_data.get('house_no', ''),
                'block_name': address_data.get('block_name', ''),
                'floor_door': address_data.get('floor_door', ''),
                'locality': address_data.get('locality', ''),
                'city': address_data.get('city', ''),
                'pincode': address_data.get('pincode', ''),
                'landmark': address_data.get('landmark', ''),
                'receiver_name': address_data.get('receiver_name', ''),
                'receiver_phone': address_data.get('receiver_phone', '')
            }
            
            # Encrypt sensitive data
            encrypted_data = AddressService._encrypt_address_data(sensitive_data)
            
            # If this is set as default, unset other defaults first
            if is_default:
                AddressService._unset_other_defaults(user_id)
            
            # Insert new address
            query = """
                INSERT INTO user_addresses 
                (user_id, encrypted_address_data, address_label, latitude, longitude, is_default)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            result = DatabaseService.execute_query(
                query, 
                (user_id, encrypted_data, address_label, latitude, longitude, is_default),
                fetch_one=True
            )
            
            return result['id'] if result else None
            
        except Exception as e:
            logger.error(f"Error saving address: {e}")
            return None
    
    @staticmethod
    def get_user_addresses(user_id: int) -> List[Dict]:
        """Get all addresses for a user with decrypted data"""
        try:
            # Initialize database service first
            DatabaseService.initialize_pool()
            
            query = """
                SELECT id, encrypted_address_data, address_label, latitude, longitude, 
                       is_default, created_at, updated_at
                FROM user_addresses 
                WHERE user_id = %s 
                ORDER BY is_default DESC, created_at DESC
            """
            addresses = DatabaseService.execute_query(query, (user_id,))
            
            if not addresses:
                return []
            
            # Decrypt and format addresses
            decrypted_addresses = []
            for addr in addresses:
                try:
                    decrypted_data = AddressService._decrypt_address_data(addr['encrypted_address_data'])
                    
                    address_info = {
                        'id': addr['id'],
                        'address_label': addr['address_label'],
                        'latitude': float(addr['latitude']) if addr['latitude'] else None,
                        'longitude': float(addr['longitude']) if addr['longitude'] else None,
                        'is_default': addr['is_default'],
                        'created_at': addr['created_at'],
                        'updated_at': addr['updated_at'],
                        **decrypted_data  # Merge decrypted sensitive data
                    }
                    decrypted_addresses.append(address_info)
                except Exception as decrypt_error:
                    logger.error(f"Error decrypting address {addr['id']}: {decrypt_error}")
                    continue
            
            return decrypted_addresses
            
        except Exception as e:
            logger.error(f"Error getting user addresses: {e}")
            return []
    
    @staticmethod
    def get_address_by_id(user_id: int, address_id: int) -> Optional[Dict]:
        """Get a specific address by ID with decrypted data"""
        try:
            query = """
                SELECT id, encrypted_address_data, address_label, latitude, longitude, 
                       is_default, created_at, updated_at
                FROM user_addresses 
                WHERE id = %s AND user_id = %s
            """
            result = DatabaseService.execute_query(query, (address_id, user_id), fetch_one=True)
            
            if not result:
                return None
            
            # Decrypt sensitive data
            decrypted_data = AddressService._decrypt_address_data(result['encrypted_address_data'])
            
            return {
                'id': result['id'],
                'address_label': result['address_label'],
                'latitude': float(result['latitude']) if result['latitude'] else None,
                'longitude': float(result['longitude']) if result['longitude'] else None,
                'is_default': result['is_default'],
                'created_at': result['created_at'],
                'updated_at': result['updated_at'],
                **decrypted_data
            }
            
        except Exception as e:
            logger.error(f"Error getting address by ID: {e}")
            return None
    
    @staticmethod
    def update_address(user_id: int, address_id: int, address_data: dict) -> bool:
        """Update an existing address"""
        try:
            # Extract non-sensitive data
            address_label = address_data.get('address_label', '')
            latitude = address_data.get('latitude')
            longitude = address_data.get('longitude')
            is_default = address_data.get('is_default', False)
            
            # Prepare sensitive data for encryption
            sensitive_data = {
                'house_no': address_data.get('house_no', ''),
                'block_name': address_data.get('block_name', ''),
                'floor_door': address_data.get('floor_door', ''),
                'locality': address_data.get('locality', ''),
                'city': address_data.get('city', ''),
                'pincode': address_data.get('pincode', ''),
                'landmark': address_data.get('landmark', ''),
                'receiver_name': address_data.get('receiver_name', ''),
                'receiver_phone': address_data.get('receiver_phone', '')
            }
            
            # Encrypt sensitive data
            encrypted_data = AddressService._encrypt_address_data(sensitive_data)
            
            # If this is set as default, unset other defaults first
            if is_default:
                AddressService._unset_other_defaults(user_id, exclude_id=address_id)
            
            # Update address
            query = """
                UPDATE user_addresses 
                SET encrypted_address_data = %s, address_label = %s, latitude = %s, 
                    longitude = %s, is_default = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            """
            result = DatabaseService.execute_query(
                query, 
                (encrypted_data, address_label, latitude, longitude, is_default, address_id, user_id)
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating address: {e}")
            return False
    
    @staticmethod
    def delete_address(user_id: int, address_id: int) -> bool:
        """Delete an address"""
        try:
            query = "DELETE FROM user_addresses WHERE id = %s AND user_id = %s"
            result = DatabaseService.execute_query(query, (address_id, user_id))
            return result is not None
            
        except Exception as e:
            logger.error(f"Error deleting address: {e}")
            return False
    
    @staticmethod
    def set_default_address(user_id: int, address_id: int) -> bool:
        """Set an address as default"""
        try:
            # First unset all defaults for user
            AddressService._unset_other_defaults(user_id)
            
            # Set the specified address as default
            query = """
                UPDATE user_addresses 
                SET is_default = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            """
            result = DatabaseService.execute_query(query, (address_id, user_id))
            return result is not None
            
        except Exception as e:
            logger.error(f"Error setting default address: {e}")
            return False
    
    @staticmethod
    def get_default_address(user_id: int) -> Optional[Dict]:
        """Get user's default address"""
        try:
            query = """
                SELECT id, encrypted_address_data, address_label, latitude, longitude, 
                       is_default, created_at, updated_at
                FROM user_addresses 
                WHERE user_id = %s AND is_default = TRUE
                LIMIT 1
            """
            result = DatabaseService.execute_query(query, (user_id,), fetch_one=True)
            
            if not result:
                return None
            
            # Decrypt sensitive data
            decrypted_data = AddressService._decrypt_address_data(result['encrypted_address_data'])
            
            return {
                'id': result['id'],
                'address_label': result['address_label'],
                'latitude': float(result['latitude']) if result['latitude'] else None,
                'longitude': float(result['longitude']) if result['longitude'] else None,
                'is_default': result['is_default'],
                'created_at': result['created_at'],
                'updated_at': result['updated_at'],
                **decrypted_data
            }
            
        except Exception as e:
            logger.error(f"Error getting default address: {e}")
            return None
    
    @staticmethod
    def _unset_other_defaults(user_id: int, exclude_id: int = None):
        """Unset default flag for all other addresses"""
        try:
            if exclude_id:
                query = """
                    UPDATE user_addresses 
                    SET is_default = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND id != %s
                """
                DatabaseService.execute_query(query, (user_id, exclude_id))
            else:
                query = """
                    UPDATE user_addresses 
                    SET is_default = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """
                DatabaseService.execute_query(query, (user_id,))
                
        except Exception as e:
            logger.error(f"Error unsetting other defaults: {e}")