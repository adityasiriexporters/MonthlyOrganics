"""
Database service layer for Monthly Organics
Centralizes database operations and connection management with connection pooling
"""
import os
import logging
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from typing import Optional, Dict, List, Any
import threading

logger = logging.getLogger(__name__)

class DatabaseService:
    """Centralized database service with connection pooling for better performance"""
    
    _connection_pool = None
    _pool_lock = threading.Lock()
    
    @classmethod
    def initialize_pool(cls):
        """Initialize connection pool once"""
        if cls._connection_pool is None:
            with cls._pool_lock:
                if cls._connection_pool is None:  # Double-check locking
                    try:
                        database_url = os.environ.get("DATABASE_URL")
                        if not database_url:
                            logger.error("DATABASE_URL environment variable not set")
                            return False
                        
                        # Create connection pool with 5-20 connections
                        cls._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                            minconn=2,
                            maxconn=10,
                            dsn=database_url
                        )
                        logger.info("Database connection pool initialized successfully")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to initialize connection pool: {e}")
                        return False
        return True
    
    @classmethod
    def get_connection(cls) -> Optional[psycopg2.extensions.connection]:
        """Get database connection from pool with proper error handling"""
        if not cls.initialize_pool():
            return None
            
        try:
            conn = cls._connection_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            return None
    
    @classmethod
    def return_connection(cls, conn: psycopg2.extensions.connection):
        """Return connection to pool"""
        if cls._connection_pool and conn:
            try:
                cls._connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")
    
    @classmethod
    def execute_query(cls, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """Execute query with connection pool management for better performance"""
        conn = None
        cursor = None
        try:
            conn = cls.get_connection()
            if not conn:
                return None
                
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = None
                
            conn.commit()
            return result
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Query execution failed: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                cls.return_connection(conn)  # Return to pool instead of closing

class CartService:
    """Service for cart-related database operations"""
    
    @staticmethod
    def get_cart_items(user_id: int) -> List[Dict]:
        """Get all cart items for a user with product details"""
        query = """
            SELECT 
                ci.variation_id,
                ci.quantity,
                pv.variation_name,
                pv.mrp as price,
                p.name as product_name,
                p.description,
                (ci.quantity * pv.mrp) as total_price
            FROM cart_items ci
            INNER JOIN product_variations pv ON ci.variation_id = pv.id
            INNER JOIN products p ON pv.product_id = p.id
            WHERE ci.user_id = %s
            ORDER BY p.name, pv.variation_name
        """
        result = DatabaseService.execute_query(query, (user_id,))
        return result if result else []
    
    @staticmethod
    def add_to_cart(user_id: int, variation_id: int) -> Optional[int]:
        """Add item to cart or update quantity using UPSERT"""
        query = """
            INSERT INTO cart_items (user_id, variation_id, quantity)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, variation_id)
            DO UPDATE SET quantity = cart_items.quantity + 1
            RETURNING quantity
        """
        result = DatabaseService.execute_query(query, (user_id, variation_id), fetch_one=True)
        return result[0] if result else None
    
    @staticmethod
    def update_cart_quantity(user_id: int, variation_id: int, action: str) -> Optional[int]:
        """Update cart item quantity (increment or decrement)"""
        if action == 'incr':
            query = """
                UPDATE cart_items 
                SET quantity = quantity + 1 
                WHERE user_id = %s AND variation_id = %s
                RETURNING quantity
            """
        elif action == 'decr':
            query = """
                UPDATE cart_items 
                SET quantity = quantity - 1 
                WHERE user_id = %s AND variation_id = %s
                RETURNING quantity
            """
        else:
            return None
            
        result = DatabaseService.execute_query(query, (user_id, variation_id), fetch_one=True)
        return result[0] if result else None
    
    @staticmethod
    def remove_cart_item(user_id: int, variation_id: int) -> bool:
        """Remove item from cart"""
        query = """
            DELETE FROM cart_items 
            WHERE user_id = %s AND variation_id = %s
        """
        result = DatabaseService.execute_query(query, (user_id, variation_id), fetch_all=False)
        return result is not None
    
    @staticmethod
    def get_cart_item_details(user_id: int, variation_id: int) -> Optional[Dict]:
        """Get single cart item details"""
        query = """
            SELECT 
                ci.variation_id,
                ci.quantity,
                pv.variation_name,
                pv.mrp as price,
                p.name as product_name,
                (ci.quantity * pv.mrp) as total_price
            FROM cart_items ci
            INNER JOIN product_variations pv ON ci.variation_id = pv.id
            INNER JOIN products p ON pv.product_id = p.id
            WHERE ci.user_id = %s AND ci.variation_id = %s
        """
        result = DatabaseService.execute_query(query, (user_id, variation_id), fetch_one=True)
        return dict(result) if result else None

class UserService:
    """Service for user-related database operations"""
    
    @staticmethod
    def find_user_by_phone(phone: str) -> Optional[Dict]:
        """Find user by phone number"""
        from models import User
        user = User.query.filter_by(phone=phone).first()
        return user
    
    @staticmethod
    def create_user(phone: str) -> Optional[Dict]:
        """Create new user with phone number"""
        from models import User, db
        try:
            user = User(
                first_name="User",
                last_name=phone[-4:],
                phone=phone,
                email=f"user{phone}@monthlyorganics.com"
            )
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
            return None