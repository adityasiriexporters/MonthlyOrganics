"""
Database service layer for Monthly Organics
Centralizes database operations and connection management
"""
import os
import logging
import psycopg2
import psycopg2.extras
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class DatabaseService:
    """Centralized database service for connection management and common queries"""
    
    @staticmethod
    def get_connection() -> Optional[psycopg2.extensions.connection]:
        """Get database connection with proper error handling"""
        try:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                logger.error("DATABASE_URL environment variable not set")
                return None
            
            conn = psycopg2.connect(database_url)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    
    @staticmethod
    def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """Execute query with proper connection management"""
        conn = None
        cursor = None
        try:
            conn = DatabaseService.get_connection()
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
                conn.close()

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