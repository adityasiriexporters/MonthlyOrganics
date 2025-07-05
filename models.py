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
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy=True, cascade='all, delete-orphan')
    addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')
    
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
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False, default='United States')
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Address {self.address_line1}, {self.city}>'

class Subscription(db.Model):
    """Subscription model for monthly organic produce deliveries."""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_type = db.Column(db.String(50), nullable=False)  # 'small', 'medium', 'large', 'family'
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'paused', 'cancelled'
    monthly_price = db.Column(db.Numeric(10, 2), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    next_delivery_date = db.Column(db.Date, nullable=True)
    delivery_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    delivery_address = db.relationship('Address', foreign_keys=[delivery_address_id])
    deliveries = db.relationship('Delivery', backref='subscription', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Subscription {self.plan_type} for User {self.user_id}>'

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

class Delivery(db.Model):
    """Delivery model for tracking monthly deliveries."""
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    estimated_delivery_time = db.Column(db.String(50), nullable=True)
    actual_delivery_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='scheduled')  # 'scheduled', 'in_transit', 'delivered', 'failed'
    tracking_number = db.Column(db.String(100), nullable=True)
    delivery_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    delivery_items = db.relationship('DeliveryItem', backref='delivery', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Delivery {self.id} for Subscription {self.subscription_id}>'

class DeliveryItem(db.Model):
    """DeliveryItem model for tracking individual products in deliveries."""
    __tablename__ = 'delivery_items'
    
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    product = db.relationship('Product', backref='delivery_items')
    
    def __repr__(self):
        return f'<DeliveryItem {self.quantity}x {self.product.name if self.product else "Unknown"}>'

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
