"""
Data encryption utilities for Monthly Organics
Provides secure encryption/decryption for sensitive customer data
"""
import os
import base64
import logging
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class DataEncryption:
    """Handles encryption and decryption of sensitive customer data"""
    
    _encryption_key = None
    _fernet = None
    
    @classmethod
    def _get_encryption_key(cls) -> bytes:
        """Generate or retrieve encryption key from environment"""
        if cls._encryption_key is None:
            # Try to get key from environment variable
            env_key = os.environ.get('ENCRYPTION_KEY')
            
            if env_key:
                # Use provided key
                cls._encryption_key = env_key.encode()
            else:
                # Generate key based on session secret (fallback)
                session_secret = os.environ.get('SESSION_SECRET', 'default-secret-key')
                
                # Use PBKDF2 to derive a key from the session secret
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'monthly_organics_salt',  # Fixed salt for consistency
                    iterations=100000,
                )
                cls._encryption_key = base64.urlsafe_b64encode(kdf.derive(session_secret.encode()))
        
        return cls._encryption_key
    
    @classmethod
    def _get_fernet(cls):
        """Get Fernet encryption instance"""
        if cls._fernet is None:
            key = cls._get_encryption_key()
            cls._fernet = Fernet(key)
        return cls._fernet
    
    @classmethod
    def encrypt_data(cls, data: str) -> Optional[str]:
        """
        Encrypt sensitive data
        Returns base64 encoded encrypted string or None if encryption fails
        """
        if not data:
            return None
        
        try:
            fernet = cls._get_fernet()
            encrypted_data = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            import traceback
            logger.error(f"Encryption traceback: {traceback.format_exc()}")
            return None
    
    @classmethod
    def decrypt_data(cls, encrypted_data: str) -> Optional[str]:
        """
        Decrypt sensitive data
        Returns decrypted string or None if decryption fails
        """
        if not encrypted_data:
            return None
        
        try:
            fernet = cls._get_fernet()
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    @classmethod
    def encrypt_phone(cls, phone: str) -> Optional[str]:
        """Encrypt phone number"""
        return cls.encrypt_data(phone)
    
    @classmethod
    def decrypt_phone(cls, encrypted_phone: str) -> Optional[str]:
        """Decrypt phone number"""
        return cls.decrypt_data(encrypted_phone)
    
    @classmethod
    def encrypt_address_field(cls, address_field: str) -> Optional[str]:
        """Encrypt address field (house number, floor, etc.)"""
        return cls.encrypt_data(address_field)
    
    @classmethod
    def decrypt_address_field(cls, encrypted_field: str) -> Optional[str]:
        """Decrypt address field"""
        return cls.decrypt_data(encrypted_field)
    
    @classmethod
    def hash_for_search(cls, data: str) -> str:
        """
        Create a hash for search purposes (one-way)
        Used for phone number lookups without storing plaintext
        """
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()

class SecureDataHandler:
    """High-level handler for secure customer data operations"""
    
    @staticmethod
    def prepare_user_data_for_storage(phone: str, first_name: str = '', last_name: str = '') -> dict:
        """Prepare user data for secure storage"""
        return {
            'phone_encrypted': DataEncryption.encrypt_phone(phone),
            'phone_hash': DataEncryption.hash_for_search(phone),  # For lookup
            'first_name': first_name,  # Names are less sensitive, but can be encrypted if needed
            'last_name': last_name
        }
    
    @staticmethod
    def prepare_address_data_for_storage(address_data: dict) -> dict:
        """Prepare address data for secure storage"""
        secure_data = address_data.copy()
        
        # Encrypt sensitive fields
        sensitive_fields = ['house_number', 'floor_door', 'contact_number', 'nearby_landmark']
        
        for field in sensitive_fields:
            if field in secure_data and secure_data[field]:
                secure_data[f'{field}_encrypted'] = DataEncryption.encrypt_address_field(secure_data[field])
                # Remove plaintext version
                del secure_data[field]
        
        # Keep non-sensitive fields as-is for search/display
        # locality, city, pincode are needed for delivery logistics
        
        return secure_data
    
    @staticmethod
    def decrypt_user_data(user_data: dict) -> dict:
        """Decrypt user data for display"""
        decrypted = user_data.copy()
        
        if 'phone_encrypted' in user_data:
            decrypted['phone'] = DataEncryption.decrypt_phone(user_data['phone_encrypted'])
        
        return decrypted
    
    @staticmethod
    def decrypt_address_data(address_data: dict) -> dict:
        """Decrypt address data for display"""
        decrypted = address_data.copy()
        
        # Decrypt sensitive fields
        encrypted_fields = {
            'house_number_encrypted': 'house_number',
            'floor_door_encrypted': 'floor_door', 
            'contact_number_encrypted': 'contact_number',
            'nearby_landmark_encrypted': 'nearby_landmark'
        }
        
        for encrypted_field, original_field in encrypted_fields.items():
            if encrypted_field in address_data and address_data[encrypted_field]:
                decrypted[original_field] = DataEncryption.decrypt_address_field(address_data[encrypted_field])
        
        return decrypted