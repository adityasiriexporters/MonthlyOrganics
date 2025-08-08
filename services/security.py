"""
Security service for Monthly Organics
Enhanced security measures for data protection
"""
import logging
import re
from typing import Dict, List, Optional
from utils.encryption import DataEncryption, SecureDataHandler
from utils.id_generator import CustomIDGenerator
from .database import DatabaseService

logger = logging.getLogger(__name__)

class SecureUserService:
    """Secure user operations with data encryption"""
    
    @staticmethod
    def find_user_by_phone(phone: str) -> Optional[Dict]:
        """Find user by phone number using encrypted phone hash"""
        try:
            # Create hash of the phone number for lookup
            phone_hash = DataEncryption.hash_for_search(phone)
            
            query = """
                SELECT id, phone_encrypted, phone_hash, first_name, last_name, custom_id,
                       created_at, is_active
                FROM users 
                WHERE phone_hash = %s AND is_active = true
            """
            user_data = DatabaseService.execute_query(query, (phone_hash,), fetch_one=True)
            
            # Convert Row object to dict and decrypt phone number for return
            if user_data:
                user_dict = dict(user_data)
                if user_dict.get('phone_encrypted'):
                    user_dict['phone'] = DataEncryption.decrypt_phone(user_dict['phone_encrypted'])
                return user_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by phone: {e}")
            return None
    
    @staticmethod
    def create_user(phone: str) -> Optional[Dict]:
        """Create new user with encrypted phone storage"""
        try:
            # Generate custom ID
            custom_id = CustomIDGenerator.generate_user_id()
            
            # Encrypt phone data
            phone_encrypted = DataEncryption.encrypt_phone(phone)
            phone_hash = DataEncryption.hash_for_search(phone)
            
            query = """
                INSERT INTO users (phone_encrypted, phone_hash, first_name, last_name, custom_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, phone_encrypted, phone_hash, first_name, last_name, custom_id, created_at
            """
            
            user_data = DatabaseService.execute_query(
                query, 
                (
                    phone_encrypted,
                    phone_hash,
                    "Customer",  # Default name
                    "",
                    custom_id
                ),
                fetch_one=True
            )
            
            # Convert Row object to dict and add decrypted phone for backwards compatibility
            if user_data:
                user_dict = dict(user_data)
                user_dict['phone'] = phone
                return user_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def create_user_with_details(phone: str, first_name: str, last_name: str) -> Optional[Dict]:
        """Create new user with provided details and encrypted phone storage"""
        try:
            # Auto-capitalize first letter of names
            first_name = first_name.strip().title() if first_name else ""
            last_name = last_name.strip().title() if last_name else ""
            
            # Generate custom ID
            custom_id = CustomIDGenerator.generate_user_id()
            
            # Encrypt phone data
            phone_encrypted = DataEncryption.encrypt_phone(phone)
            phone_hash = DataEncryption.hash_for_search(phone)
            
            query = """
                INSERT INTO users (phone_encrypted, phone_hash, first_name, last_name, custom_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, phone_encrypted, phone_hash, first_name, last_name, custom_id, created_at
            """
            
            user_data = DatabaseService.execute_query(
                query, 
                (
                    phone_encrypted,
                    phone_hash,
                    first_name,
                    last_name,
                    custom_id
                ),
                fetch_one=True
            )
            
            # Convert Row object to dict and add decrypted phone for backwards compatibility
            if user_data:
                user_dict = dict(user_data)
                user_dict['phone'] = phone
                return user_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating user with details: {e}")
            return None
    
    @staticmethod
    def update_user_name(user_id: int, first_name: str, last_name: str) -> bool:
        """Update user's first and last name"""
        try:
            # Auto-capitalize first letter of names
            first_name = first_name.strip().title() if first_name else ""
            last_name = last_name.strip().title() if last_name else ""
            
            query = """
                UPDATE users 
                SET first_name = %s, last_name = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            DatabaseService.execute_query(query, (first_name, last_name, user_id))
            return True
            
        except Exception as e:
            logger.error(f"Error updating user name: {e}")
            return False

class SecureAddressService:
    """Secure address operations with data encryption"""
    
    @staticmethod
    def get_user_addresses(user_custom_id: str) -> List[Dict]:
        """Get user addresses with decryption using custom_id"""
        try:
            query = """
                SELECT id, user_custom_id, nickname, house_number_encrypted, block_name,
                       floor_door_encrypted, contact_number_encrypted, latitude, longitude,
                       locality, city, pincode, nearby_landmark_encrypted, 
                       address_notes, receiver_name_encrypted, is_default, created_at
                FROM addresses 
                WHERE user_custom_id = %s 
                ORDER BY is_default DESC, created_at DESC
            """
            addresses = DatabaseService.execute_query(query, (user_custom_id,), fetch_all=True)
            
            if addresses:
                # Decrypt sensitive data for each address
                decrypted_addresses = []
                for addr in addresses:
                    try:
                        from utils.encryption import SecureDataHandler
                        decrypted_addr = SecureDataHandler.decrypt_address_data(addr)
                        # Add computed fields for template display
                        decrypted_addr['house_flat'] = decrypted_addr.get('house_number', '') or decrypted_addr.get('floor_door', '')
                        decrypted_addr['area'] = addr.get('locality', '') or addr.get('city', '')
                        decrypted_addr['landmark'] = decrypted_addr.get('nearby_landmark', '')
                        decrypted_addr['receiver_phone'] = decrypted_addr.get('contact_number', '')
                        decrypted_addresses.append(decrypted_addr)
                    except Exception as decrypt_error:
                        logger.error(f"Error decrypting address {addr.get('id', 'unknown')}: {decrypt_error}")
                        # Fallback to basic data
                        basic_addr = {
                            'id': addr.get('id'),
                            'nickname': addr.get('nickname', 'Address'),
                            'is_default': addr.get('is_default', False),
                            'house_flat': '',
                            'area': addr.get('locality', '') or addr.get('city', ''),
                            'landmark': '',
                            'pincode': addr.get('pincode', ''),
                            'receiver_name': 'Customer',
                            'receiver_phone': ''
                        }
                        decrypted_addresses.append(basic_addr)
                return decrypted_addresses
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting user addresses: {e}")
            return []
    
    @staticmethod
    def create_address(user_custom_id: str, address_data: Dict) -> Optional[int]:
        """Create address with encrypted sensitive data using custom_id"""
        try:
            # Prepare secure address data
            secure_data = SecureDataHandler.prepare_address_data_for_storage(address_data)
            
            # If this is set as default, unset other defaults first
            if secure_data.get('is_default'):
                DatabaseService.execute_query(
                    "UPDATE addresses SET is_default = false WHERE user_custom_id = %s",
                    (user_custom_id,),
                    fetch_one=False,
                    fetch_all=False
                )
            
            # Encrypted insertion for security
            query = """
                INSERT INTO addresses (
                    user_custom_id, nickname, house_number_encrypted, block_name, floor_door_encrypted, 
                    contact_number_encrypted, latitude, longitude, locality, city, pincode, 
                    nearby_landmark_encrypted, address_notes, receiver_name_encrypted, is_default
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            result = DatabaseService.execute_query(
                query,
                (
                    user_custom_id,
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
                    secure_data.get('nearby_landmark_encrypted'),
                    secure_data.get('address_notes', ''),
                    secure_data.get('receiver_name_encrypted'),
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
    def set_default_address(address_id: int, user_custom_id: str) -> bool:
        """Set an address as default using custom_id"""
        try:
            # First unset all defaults for this user
            DatabaseService.execute_query(
                "UPDATE addresses SET is_default = false WHERE user_custom_id = %s",
                (user_custom_id,),
                fetch_one=False,
                fetch_all=False
            )
            
            # Set the specified address as default
            result = DatabaseService.execute_query(
                "UPDATE addresses SET is_default = true WHERE id = %s AND user_custom_id = %s",
                (address_id, user_custom_id),
                fetch_one=False,
                fetch_all=False
            )
            
            # Check if any rows were affected
            return result is not None and result > 0
            
        except Exception as e:
            logger.error(f"Error setting default address: {e}")
            return False
    
    @staticmethod
    def update_address(address_id: int, user_custom_id: str, address_data: Dict) -> bool:
        """Update an existing address with encrypted sensitive data using custom_id"""
        try:
            # Prepare secure address data
            secure_data = SecureDataHandler.prepare_address_data_for_storage(address_data)
            
            # If this is set as default, unset other defaults first
            if secure_data.get('is_default'):
                DatabaseService.execute_query(
                    "UPDATE addresses SET is_default = false WHERE user_custom_id = %s AND id != %s",
                    (user_custom_id, address_id),
                    fetch_one=False,
                    fetch_all=False
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
                    receiver_name_encrypted = %s,
                    is_default = %s
                WHERE id = %s AND user_custom_id = %s
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
                    secure_data.get('nearby_landmark_encrypted'),
                    secure_data.get('address_notes', ''),
                    secure_data.get('receiver_name_encrypted'),
                    secure_data.get('is_default', False),
                    address_id,
                    user_custom_id
                ),
                fetch_one=False,
                fetch_all=False
            )
            
            # Check if any rows were affected
            return result is not None and result > 0
            
        except Exception as e:
            logger.error(f"Error updating address: {e}")
            return False
    
    @staticmethod
    def delete_address(address_id: int, user_custom_id: str) -> bool:
        """Delete an address using custom_id"""
        try:
            result = DatabaseService.execute_query(
                "DELETE FROM addresses WHERE id = %s AND user_custom_id = %s",
                (address_id, user_custom_id),
                fetch_one=False,
                fetch_all=False
            )
            
            # Check if any rows were affected
            return result is not None and result > 0
            
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