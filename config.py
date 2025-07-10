"""
Configuration settings for Monthly Organics
Centralizes all application configuration
"""
import os
from typing import Dict, Any


class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # External services
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    
    # Business logic constants
    DELIVERY_FEE = 50.00
    FREE_DELIVERY_THRESHOLD = 500.00
    
    # Security settings
    OTP_EXPIRY_MINUTES = 10
    MAX_OTP_ATTEMPTS = 3
    
    # Development settings
    TESTING_OTP = "290921"  # Will be removed in production
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate required configuration"""
        missing = []
        if not cls.SECRET_KEY:
            missing.append('SESSION_SECRET')
        if not cls.SQLALCHEMY_DATABASE_URI:
            missing.append('DATABASE_URL')
            
        return {
            'valid': len(missing) == 0,
            'missing': missing
        }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    

# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}