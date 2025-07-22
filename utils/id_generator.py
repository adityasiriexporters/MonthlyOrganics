"""
Custom ID Generator for Monthly Organics
Generates user IDs in format: YYQSSSS or YYQNSSSS
Where:
- YY: Last two digits of year
- Q: Quarter (1-4)
- N: Additional digit when sequence exceeds 9999 (optional)
- SSSS: Sequential number (0001-9999)
"""

import logging
from datetime import datetime
from typing import Optional
from services.database import DatabaseService

logger = logging.getLogger(__name__)

class CustomIDGenerator:
    """Generates custom user IDs based on year, quarter, and sequence"""
    
    @staticmethod
    def get_current_quarter() -> int:
        """Get current quarter (1-4) based on current month"""
        month = datetime.now().month
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4
    
    @staticmethod
    def get_current_year_suffix() -> str:
        """Get last two digits of current year"""
        return str(datetime.now().year)[-2:]
    
    @staticmethod
    def generate_user_id() -> str:
        """Generate next available user ID in the format YYQSSSS or YYQNSSSS"""
        try:
            year_suffix = CustomIDGenerator.get_current_year_suffix()
            quarter = CustomIDGenerator.get_current_quarter()
            
            # Base prefix (year + quarter)
            base_prefix = f"{year_suffix}{quarter}"
            
            # Find the highest existing ID for this year-quarter combination
            query = """
                SELECT custom_id FROM users 
                WHERE custom_id LIKE %s 
                ORDER BY custom_id DESC 
                LIMIT 1
            """
            
            # Search for IDs starting with base prefix
            pattern = f"{base_prefix}%"
            result = DatabaseService.execute_query(query, (pattern,), fetch_one=True)
            
            if not result:
                # First user in this year-quarter
                return f"{base_prefix}0001"
            
            last_id = result['custom_id']
            
            # Extract the sequential part
            if len(last_id) == 7:  # Format: YYQSSSS
                sequence_part = last_id[3:]  # Last 4 digits
                additional_digit = ""
            else:  # Format: YYQNSSSS (8 digits)
                additional_digit = last_id[3]
                sequence_part = last_id[4:]  # Last 4 digits
            
            # Convert to integer and increment
            current_sequence = int(sequence_part)
            
            if current_sequence >= 9999:
                # Need to add additional digit or increment it
                if additional_digit == "":
                    # First overflow, add digit '2'
                    return f"{base_prefix}20001"
                else:
                    # Increment additional digit
                    new_additional = str(int(additional_digit) + 1)
                    return f"{base_prefix}{new_additional}0001"
            else:
                # Normal increment
                new_sequence = current_sequence + 1
                if additional_digit:
                    return f"{base_prefix}{additional_digit}{new_sequence:04d}"
                else:
                    return f"{base_prefix}{new_sequence:04d}"
                    
        except Exception as e:
            logger.error(f"Error generating custom user ID: {e}")
            # Fallback to timestamp-based ID
            year_suffix = CustomIDGenerator.get_current_year_suffix()
            quarter = CustomIDGenerator.get_current_quarter()
            timestamp = int(datetime.now().timestamp())
            return f"{year_suffix}{quarter}{timestamp % 10000:04d}"
    
    @staticmethod
    def validate_custom_id(custom_id: str) -> bool:
        """Validate if custom ID follows the correct format"""
        if not custom_id:
            return False
            
        # Check length (7 or 8 digits)
        if len(custom_id) not in [7, 8]:
            return False
            
        # Check if all characters are digits
        if not custom_id.isdigit():
            return False
            
        # Check year suffix (first 2 digits)
        year_suffix = custom_id[:2]
        if not (0 <= int(year_suffix) <= 99):
            return False
            
        # Check quarter (3rd digit)
        quarter = int(custom_id[2])
        if quarter not in [1, 2, 3, 4]:
            return False
            
        return True