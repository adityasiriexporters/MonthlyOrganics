from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import os

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    """User model for Monthly Organics customers."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships - kept for future expansion
    # subscriptions = db.relationship('Subscription', backref='user', lazy=True, cascade='all, delete-orphan')
    # addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Address(db.Model):
    """Address model for user delivery addresses."""
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nickname = db.Column(db.String(50), nullable=False)  # Mandatory
    house_number = db.Column(db.String(100), nullable=False)  # Mandatory
    block_name = db.Column(db.String(100), nullable=True)
    floor_door = db.Column(db.String(50), nullable=False)  # Mandatory
    contact_number = db.Column(db.String(20), nullable=False)  # Mandatory
    latitude = db.Column(db.Float, nullable=False)  # Mandatory - from map
    longitude = db.Column(db.Float, nullable=False)  # Mandatory - from map
    locality = db.Column(db.String(100), nullable=False)  # Mandatory - from map, editable
    city = db.Column(db.String(100), nullable=False)  # From map, non-editable
    pincode = db.Column(db.String(10), nullable=False)  # From map, non-editable
    nearby_landmark = db.Column(db.String(200), nullable=True)
    address_notes = db.Column(db.Text, nullable=True)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('addresses', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Address {self.nickname} - {self.user_id}>'
    
    @property
    def full_address(self):
        """Get formatted full address string."""
        address_parts = [
            self.house_number,
            self.block_name,
            self.floor_door,
            self.locality,
            self.city,
            self.pincode
        ]
        return ', '.join([part for part in address_parts if part])

# Removed Subscription model - not needed for current e-commerce functionality  
# Will be added back when implementing subscription features

class Product(db.Model):
    """Product model for organic produce items."""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # 'fruit', 'vegetable', 'herb', 'grain'
    season = db.Column(db.String(20), nullable=True)  # 'spring', 'summer', 'fall', 'winter', 'year-round'
    origin_farm = db.Column(db.String(100), nullable=True)
    organic_certified = db.Column(db.Boolean, default=True, nullable=False)
    price_per_unit = db.Column(db.Numeric(10, 2), nullable=True)
    unit_type = db.Column(db.String(20), nullable=False, default='piece')  # 'piece', 'pound', 'bunch', 'bag'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Product {self.name}>'

# Removed Delivery model - not needed for current e-commerce functionality
# Will be added back when implementing delivery tracking features

# Removed DeliveryItem model - not needed for current e-commerce functionality
# Will be added back when implementing delivery tracking features

# Database initialization function
def init_db(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Database tables created successfully")
            
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
