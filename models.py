from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    """User model for Monthly Organics customers."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_encrypted = db.Column(db.Text, nullable=True)  # Encrypted phone number
    phone_hash = db.Column(db.String(255), nullable=True, index=True)  # Hash for searching
    custom_id = db.Column(db.String(20), nullable=True, unique=True)  # Custom user ID format
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships will be added when needed
    
    def __repr__(self):
        return f'<User {self.custom_id or self.id}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def phone(self):
        """Decrypt and return phone number for backwards compatibility"""
        if self.phone_encrypted:
            try:
                from utils.encryption import DataEncryption
                decrypted = DataEncryption.decrypt_phone(self.phone_encrypted)
                return decrypted if decrypted else None
            except Exception:
                return None
        return None
    
    def set_phone(self, phone_number: str):
        """Set phone number with automatic encryption"""
        if phone_number:
            from utils.encryption import DataEncryption
            self.phone_encrypted = DataEncryption.encrypt_phone(phone_number)
            self.phone_hash = DataEncryption.hash_for_search(phone_number)
        else:
            self.phone_encrypted = None
            self.phone_hash = None

# Address and Subscription models handled through service layer

class Product(db.Model):
    """Product model for organic produce items."""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, nullable=False)  # References categories table
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Product {self.name}>'

# Additional models handled through service layer

class DeliveryZone(db.Model):
    """Delivery zone model for managing hyper-local delivery areas."""
    __tablename__ = 'delivery_zones'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    geometry = db.Column(db.Text, nullable=False)  # PostGIS GEOMETRY stored as text for SQLAlchemy
    geojson = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<DeliveryZone {self.name}>'


class DeliveryZoneFreeDate(db.Model):
    """Free delivery dates for specific zones."""
    __tablename__ = 'delivery_zone_free_dates'

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('delivery_zones.id'), nullable=False)
    free_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    zone = db.relationship('DeliveryZone', backref=db.backref('free_dates', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint('zone_id', 'free_date'),)

    def __repr__(self):
        return f'<DeliveryZoneFreeDate Zone:{self.zone_id} Date:{self.free_date}>'


class ZohoToken(db.Model):
    """Model to store Zoho OAuth tokens."""
    __tablename__ = 'zoho_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_in = db.Column(db.Integer, nullable=True)  # Token expiry in seconds
    token_type = db.Column(db.String(50), default='Bearer', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<ZohoToken {self.id}>'
    
    @property
    def is_expired(self):
        """Check if the access token is expired."""
        if not self.expires_in:
            return False
        
        expiry_time = self.updated_at.timestamp() + self.expires_in
        current_time = datetime.utcnow().timestamp()
        return current_time >= expiry_time

# Database initialization function
def init_db(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Add sample data if tables are empty
            if Product.query.count() == 0:
                sample_products = [
                    Product(name='Organic Apples', description='Fresh organic apples from local orchards', 
                           category='fruit', season='fall', origin_farm='Green Valley Farm', 
                           price_per_unit=2.50, unit_type='pound'),
                    Product(name='Organic Carrots', description='Sweet organic carrots grown locally', 
                           category='vegetable', season='year-round', origin_farm='Sunrise Gardens', 
                           price_per_unit=1.75, unit_type='pound'),
                    Product(name='Organic Spinach', description='Fresh organic spinach leaves', 
                           category='vegetable', season='spring', origin_farm='Healthy Harvest Farm', 
                           price_per_unit=3.25, unit_type='bunch'),
                    Product(name='Organic Tomatoes', description='Vine-ripened organic tomatoes', 
                           category='vegetable', season='summer', origin_farm='Sunny Acres', 
                           price_per_unit=4.00, unit_type='pound'),
                    Product(name='Organic Basil', description='Fresh organic basil for cooking', 
                           category='herb', season='summer', origin_farm='Herb Haven', 
                           price_per_unit=2.00, unit_type='bunch')
                ]
                
                for product in sample_products:
                    db.session.add(product)
                
                db.session.commit()
                print("Sample products added to database")
                
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
