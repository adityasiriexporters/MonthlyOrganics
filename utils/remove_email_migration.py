
from services.database import DatabaseService
import logging

logger = logging.getLogger(__name__)

class EmailRemovalMigration:
    """Migration to safely remove email column from users table"""
    
    @staticmethod
    def remove_email_column():
        """Remove email column from users table"""
        try:
            # First, drop the unique constraint and index
            logger.info("Dropping email constraints and index...")
            
            # Drop unique constraint (if exists)
            try:
                DatabaseService.execute_query(
                    "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key",
                    fetch_one=False,
                    fetch_all=False
                )
            except Exception as e:
                logger.warning(f"Could not drop email unique constraint: {e}")
            
            # Drop index (if exists)
            try:
                DatabaseService.execute_query(
                    "DROP INDEX IF EXISTS ix_users_email",
                    fetch_one=False,
                    fetch_all=False
                )
            except Exception as e:
                logger.warning(f"Could not drop email index: {e}")
            
            # Drop the email column
            logger.info("Dropping email column...")
            DatabaseService.execute_query(
                "ALTER TABLE users DROP COLUMN IF EXISTS email",
                fetch_one=False,
                fetch_all=False
            )
            
            logger.info("Successfully removed email column from users table")
            return True
            
        except Exception as e:
            logger.error(f"Error removing email column: {e}")
            return False
    
    @staticmethod
    def run_migration():
        """Run the complete email removal migration"""
        logger.info("Starting email column removal migration...")
        
        if EmailRemovalMigration.remove_email_column():
            logger.info("Email removal migration completed successfully")
            return True
        else:
            logger.error("Email removal migration failed")
            return False
