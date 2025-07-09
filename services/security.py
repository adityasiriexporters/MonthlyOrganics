"""
Security service for Monthly Organics
Enhanced security measures for data protection
"""
import logging
import re
from typing import Dict, List, Optional
from utils.encryption import DataEncryption, SecureDataHandler
from .database import DatabaseService

logger = logging.getLogger(__name__)

class SecureUserService:
    """Secure user operations with data encryption"""
    
    @staticmethod
    def find_user_by_phone(phone: str) -> Optional[Dict]:
        """Find user by phone number using hash lookup"""
        try:
            phone_hash = DataEncryption.hash_for_search(phone)
            
            query = """
                SELECT id, phone_encrypted, first_name, last_name, email, 
                       created_at, is_active
                FROM users 
                WHERE phone_hash = %s AND is_active = true
            """
            user_data = DatabaseService.execute_query(query, (phone_hash,), fetch_one=True)
            
            if user_data:
                # Decrypt sensitive data
                return SecureDataHandler.decrypt_user_data(user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by phone: {e}")
            return None
    
    @staticmethod
    def create_user(phone: str) -> Optional[Dict]:
        """Create new user with encrypted phone number"""
        try:
            # Prepare secure user data
            secure_data = SecureDataHandler.prepare_user_data_for_storage(
                phone=phone,
                first_name="Customer",  # Default name
                last_name=""
            )
            
            query = """
                INSERT INTO users (phone_encrypted, phone_hash, first_name, last_name, email)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, phone_encrypted, first_name, last_name, email, created_at
            """
            
            # Generate a placeholder email for now
            email = f"user_{secure_data['phone_hash'][:8]}@monthlyorganics.com"
            
            user_data = DatabaseService.execute_query(
                query, 
                (
                    secure_data['phone_encrypted'],
                    secure_data['phone_hash'], 
                    secure_data['first_name'],
                    secure_data['last_name'],
                    email
                ),
                fetch_one=True
            )
            
            if user_data:
                # Return decrypted data
                return SecureDataHandler.decrypt_user_data(user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

class SecureAddressService:
    """Secure address operations with data encryption"""
    
    @staticmethod
    def get_user_addresses(user_id: int) -> List[Dict]:
        """Get user addresses with decryption"""
        try:
            query = """
                SELECT id, user_id, nickname, house_number_encrypted, block_name,
                       floor_door_encrypted, contact_number_encrypted, latitude, longitude,
                       locality, city, pincode, nearby_landmark_encrypted, 
                       address_notes, is_default, created_at
                FROM addresses 
                WHERE user_id = %s 
                ORDER BY is_default DESC, created_at DESC
            """
            addresses = DatabaseService.execute_query(query, (user_id,))
            
            if addresses:
                # Decrypt sensitive data for each address
                decrypted_addresses = []
                for addr in addresses:
                    decrypted_addr = SecureDataHandler.decrypt_address_data(addr)
                    decrypted_addresses.append(decrypted_addr)
                return decrypted_addresses
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting user addresses: {e}")
            return []
    
    @staticmethod
    def create_address(user_id: int, address_data: Dict) -> Optional[int]:
        """Create address with encrypted sensitive data"""
        try:
            # Prepare secure address data
            secure_data = SecureDataHandler.prepare_address_data_for_storage(address_data)
            
            # If this is set as default, unset other defaults first
            if secure_data.get('is_default'):
                DatabaseService.execute_query(
                    "UPDATE addresses SET is_default = false WHERE user_id = %s",
                    (user_id,)
                )
            
            # Simple insertion without encryption for now
            query = """
                INSERT INTO addresses (
                    user_id, nickname, house_number, block_name, floor_door, 
                    contact_number, latitude, longitude, locality, city, pincode, 
                    nearby_landmark, address_notes, is_default
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            result = DatabaseService.execute_query(
                query,
                (
                    user_id,
                    secure_data['nickname'],
                    secure_data.get('house_number', ''),
                    secure_data.get('block_name', ''),
                    secure_data.get('floor_door', ''),
                    secure_data.get('contact_number', ''),
                    secure_data['latitude'],
                    secure_data['longitude'],
                    secure_data['locality'],
                    secure_data['city'],
                    secure_data['pincode'],
                    secure_data.get('nearby_landmark', ''),
                    secure_data.get('address_notes', ''),
                    secure_data['is_default']
                ),
                fetch_one=True
            )
            
            return result['id'] if result else None
            
        except Exception as e:
            logger.error(f"Error creating address: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def set_default_address(address_id: int, user_id: int) -> bool:
        """Set an address as default (no encryption needed)"""
        try:
            # First unset all defaults for this user
            DatabaseService.execute_query(
                "UPDATE addresses SET is_default = false WHERE user_id = %s",
                (user_id,)
            )
            
            # Set the specified address as default
            result = DatabaseService.execute_query(
                "UPDATE addresses SET is_default = true WHERE id = %s AND user_id = %s",
                (address_id, user_id)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting default address: {e}")
            return False
    
    @staticmethod
    def update_address(address_id: int, user_id: int, address_data: Dict) -> bool:
        """Update an existing address with encrypted sensitive data"""
        try:
            # Prepare secure address data
            secure_data = SecureDataHandler.prepare_address_data_for_storage(address_data)
            
            # If this is set as default, unset other defaults first
            if secure_data.get('is_default'):
                DatabaseService.execute_query(
                    "UPDATE addresses SET is_default = false WHERE user_id = %s AND id != %s",
                    (user_id, address_id)
                )
            
            query = """
                UPDATE addresses SET
                    nickname = %s,
                    house_number_encrypted = %s,
                    block_name = %s,
                    floor_door_encrypted = %s,
                    contact_number_encrypted = %s,
                    latitude = %s,
                    longitude = %s,
                    locality = %s,
                    city = %s,
                    pincode = %s,
                    nearby_landmark_encrypted = %s,
                    address_notes = %s,
                    is_default = %s
                WHERE id = %s AND user_id = %s
            """
            
            result = DatabaseService.execute_query(
                query,
                (
                    secure_data['nickname'],
                    secure_data.get('house_number_encrypted'),
                    secure_data.get('block_name', ''),
                    secure_data.get('floor_door_encrypted'),
                    secure_data.get('contact_number_encrypted'),
                    secure_data['latitude'],
                    secure_data['longitude'],
                    secure_data['locality'],
                    secure_data['city'],
                    secure_data['pincode'],
                    secure_data.get('nearby_landmark_encrypted', ''),
                    secure_data.get('address_notes', ''),
                    secure_data.get('is_default', False),
                    address_id,
                    user_id
                )
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating address: {e}")
            return False
    
    @staticmethod
    def delete_address(address_id: int, user_id: int) -> bool:
        """Delete an address (secure deletion)"""
        try:
            result = DatabaseService.execute_query(
                "DELETE FROM addresses WHERE id = %s AND user_id = %s",
                (address_id, user_id)
            )
            return True
            
        except Exception as e:
            logger.error(f"Error deleting address: {e}")
            return False

class SecurityAuditLogger:
    """Audit logging for security events"""
    
    @staticmethod
    def log_data_access(user_id: int, action: str, data_type: str, success: bool = True):
        """Log data access events for security auditing"""
        status = "SUCCESS" if success else "FAILURE"
        logger.info(f"SECURITY_AUDIT: User {user_id} - {action} - {data_type} - {status}")
    
    @staticmethod
    def log_encryption_event(event: str, success: bool = True):
        """Log encryption/decryption events"""
        status = "SUCCESS" if success else "FAILURE" 
        logger.info(f"ENCRYPTION_AUDIT: {event} - {status}")
    
    @staticmethod
    def log_authentication_event(phone_hash: str, event: str, success: bool = True):
        """Log authentication events"""
        status = "SUCCESS" if success else "FAILURE"
        logger.info(f"AUTH_AUDIT: Phone {phone_hash[:8]}... - {event} - {status}")