"""
Form validation utilities for Monthly Organics
Centralized validation logic for better code organization
"""
import re
from typing import Dict, List, Optional, Tuple

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class FormValidator:
    """Centralized form validation class"""
    
    @staticmethod
    def validate_mobile_number(mobile_number: str) -> bool:
        """Validate Indian mobile number format"""
        return bool(mobile_number and re.match(r'^[6-9]\d{9}$', mobile_number))
    
    @staticmethod
    def validate_otp(otp: str) -> bool:
        """Validate OTP format"""
        return bool(otp and re.match(r'^\d{6}$', otp))
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate name - only alphabets and spaces allowed"""
        return bool(name and re.match(r'^[A-Za-z\s]+$', name.strip()) and len(name.strip()) >= 2)
    
    @staticmethod
    def validate_first_name(first_name: str) -> Tuple[bool, str]:
        """Validate first name with specific error message"""
        name = first_name.strip() if first_name else ''
        if not name:
            return False, 'First name is required'
        if len(name) < 2:
            return False, 'First name must be at least 2 characters long'
        if not re.match(r'^[A-Za-z\s]+$', name):
            return False, 'First name can only contain letters and spaces'
        return True, ''
    
    @staticmethod
    def validate_last_name(last_name: str) -> Tuple[bool, str]:
        """Validate last name with specific error message"""
        name = last_name.strip() if last_name else ''
        if not name:
            return False, 'Last name is required'
        if len(name) < 2:
            return False, 'Last name must be at least 2 characters long'
        if not re.match(r'^[A-Za-z\s]+$', name):
            return False, 'Last name can only contain letters and spaces'
        return True, ''
    
    @staticmethod
    def validate_address_data(address_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate address form data
        Returns (is_valid, error_messages)
        """
        errors = []
        
        # Required fields validation
        required_fields = {
            'nickname': 'Address nickname',
            'house_number': 'House number',
            'floor_door': 'Floor/Door',
            'contact_number': 'Contact number',
            'receiver_name': 'Receiver\'s name',
            'locality': 'Locality',
            'city': 'City',
            'pincode': 'Pincode'
        }
        
        for field, label in required_fields.items():
            if not address_data.get(field, '').strip():
                errors.append(f'{label} is required')
        
        # Validate coordinates
        latitude = address_data.get('latitude', 0)
        longitude = address_data.get('longitude', 0)
        
        if latitude == 0 or longitude == 0:
            errors.append('Please select a location on the map')
        
        # Validate pincode format
        pincode = address_data.get('pincode', '').strip()
        if pincode and not re.match(r'^\d{6}$', pincode):
            errors.append('Pincode must be 6 digits')
        
        # Validate contact number
        contact_number = address_data.get('contact_number', '').strip()
        if contact_number and not re.match(r'^[6-9]\d{9}$', contact_number):
            errors.append('Contact number must be a valid 10-digit mobile number')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input"""
        return value.strip() if value else ''
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """Validate geographical coordinates"""
        return (
            -90 <= latitude <= 90 and
            -180 <= longitude <= 180 and
            not (latitude == 0 and longitude == 0)
        )