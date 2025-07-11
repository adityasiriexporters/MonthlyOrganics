"""
Data migration utility for encrypting existing customer data
One-time script to encrypt sensitive data already in the database
"""
import logging
from services.database import DatabaseService
from utils.encryption import DataEncryption, SecureDataHandler

logger = logging.getLogger(__name__)

class DataMigration:
    """Handles migration of existing plaintext data to encrypted format"""
    
    @staticmethod
    def migrate_user_phones():
        """Migrate existing user phone numbers to encrypted format"""
        try:
            # Get users with plaintext phone numbers (where encrypted columns are empty)
            query = """
                SELECT id, phone 
                FROM users 
                WHERE phone IS NOT NULL 
                AND (phone_encrypted IS NULL OR phone_hash IS NULL)
            """
            users = DatabaseService.execute_query(query)
            
            if not users:
                logger.info("No users found requiring phone number encryption")
                return True
            
            migrated_count = 0
            for user in users:
                try:
                    phone = user['phone']
                    user_id = user['id']
                    
                    # Prepare encrypted data
                    secure_data = SecureDataHandler.prepare_user_data_for_storage(phone)
                    
                    # Update user with encrypted data
                    update_query = """
                        UPDATE users 
                        SET phone_encrypted = %s, phone_hash = %s
                        WHERE id = %s
                    """
                    DatabaseService.execute_query(
                        update_query,
                        (
                            secure_data['phone_encrypted'],
                            secure_data['phone_hash'],
                            user_id
                        )
                    )
                    
                    migrated_count += 1
                    logger.info(f"Encrypted phone for user {user_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to encrypt phone for user {user['id']}: {e}")
                    continue
            
            logger.info(f"Successfully migrated {migrated_count} user phone numbers")
            return True
            
        except Exception as e:
            logger.error(f"Error migrating user phones: {e}")
            return False
    
    @staticmethod
    def migrate_address_data():
        """Migrate existing address sensitive fields to encrypted format"""
        try:
            # Get addresses with plaintext sensitive data
            query = """
                SELECT id, house_number, floor_door, contact_number, nearby_landmark
                FROM addresses 
                WHERE (house_number IS NOT NULL OR floor_door IS NOT NULL 
                       OR contact_number IS NOT NULL OR nearby_landmark IS NOT NULL)
                AND (house_number_encrypted IS NULL OR floor_door_encrypted IS NULL 
                     OR contact_number_encrypted IS NULL OR nearby_landmark_encrypted IS NULL)
            """
            addresses = DatabaseService.execute_query(query)
            
            if not addresses:
                logger.info("No addresses found requiring encryption")
                return True
            
            migrated_count = 0
            for address in addresses:
                try:
                    address_id = address['id']
                    
                    # Prepare address data for encryption
                    address_data = {
                        'house_number': address.get('house_number', ''),
                        'floor_door': address.get('floor_door', ''),
                        'contact_number': address.get('contact_number', ''),
                        'nearby_landmark': address.get('nearby_landmark', '')
                    }
                    
                    # Encrypt sensitive fields
                    secure_data = SecureDataHandler.prepare_address_data_for_storage(address_data)
                    
                    # Update address with encrypted data
                    update_query = """
                        UPDATE addresses 
                        SET house_number_encrypted = %s,
                            floor_door_encrypted = %s,
                            contact_number_encrypted = %s,
                            nearby_landmark_encrypted = %s
                        WHERE id = %s
                    """
                    DatabaseService.execute_query(
                        update_query,
                        (
                            secure_data.get('house_number_encrypted', ''),
                            secure_data.get('floor_door_encrypted', ''),
                            secure_data.get('contact_number_encrypted', ''),
                            secure_data.get('nearby_landmark_encrypted', ''),
                            address_id
                        )
                    )
                    
                    migrated_count += 1
                    logger.info(f"Encrypted sensitive data for address {address_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to encrypt address {address['id']}: {e}")
                    continue
            
            logger.info(f"Successfully migrated {migrated_count} addresses")
            return True
            
        except Exception as e:
            logger.error(f"Error migrating address data: {e}")
            return False
    
    @staticmethod
    def run_full_migration():
        """Run complete data migration"""
        logger.info("Starting data encryption migration...")
        
        success = True
        
        # Migrate user phone numbers
        if not DataMigration.migrate_user_phones():
            success = False
        
        # Migrate address data
        if not DataMigration.migrate_address_data():
            success = False
        
        if success:
            logger.info("Data migration completed successfully")
        else:
            logger.error("Data migration completed with errors")
        
        return success
    
    @staticmethod
    def verify_migration():
        """Verify that migration was successful"""
        try:
            # Check users
            user_query = """
                SELECT COUNT(*) as total_users,
                       COUNT(phone_encrypted) as encrypted_phones,
                       COUNT(phone_hash) as hashed_phones
                FROM users 
                WHERE phone IS NOT NULL
            """
            user_stats = DatabaseService.execute_query(user_query, fetch_one=True)
            
            # Check addresses
            address_query = """
                SELECT COUNT(*) as total_addresses,
                       COUNT(house_number_encrypted) as encrypted_house_numbers,
                       COUNT(contact_number_encrypted) as encrypted_contacts
                FROM addresses 
                WHERE house_number IS NOT NULL OR contact_number IS NOT NULL
            """
            address_stats = DatabaseService.execute_query(address_query, fetch_one=True)
            
            logger.info(f"Migration Verification:")
            logger.info(f"Users: {user_stats['encrypted_phones']}/{user_stats['total_users']} phones encrypted")
            logger.info(f"Addresses: {address_stats['encrypted_house_numbers']}/{address_stats['total_addresses']} house numbers encrypted")
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying migration: {e}")
            return False