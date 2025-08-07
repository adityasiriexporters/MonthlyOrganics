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
    def _is_connection_healthy(cls, conn: psycopg2.extensions.connection) -> bool:
        """Check if a database connection is healthy"""
        try:
            if conn is None or conn.closed != 0:
                return False
            
            # Test the connection with a simple query
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
            
        except Exception as e:
            logger.debug(f"Connection health check failed: {e}")  # Reduce log noise
            return False
    
    @classmethod
    def get_connection(cls) -> Optional[psycopg2.extensions.connection]:
        """Get database connection from pool with proper error handling and health checks"""
        if not cls.initialize_pool():
            return None
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = cls._connection_pool.getconn()
                if conn is None:
                    continue
                
                # Check if connection is healthy
                if cls._is_connection_healthy(conn):
                    return conn
                else:
                    # Connection is unhealthy, remove it from pool and try again
                    logger.debug(f"Unhealthy connection detected on attempt {attempt + 1}, removing from pool")
                    cls._connection_pool.putconn(conn, close=True)
                    
            except Exception as e:
                logger.error(f"Failed to get connection from pool (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                    
        return None
    
    @classmethod
    def return_connection(cls, conn: psycopg2.extensions.connection, close_conn: bool = False):
        """Return connection to pool or close it if it's unhealthy"""
        if cls._connection_pool and conn:
            try:
                if close_conn or not cls._is_connection_healthy(conn):
                    cls._connection_pool.putconn(conn, close=True)
                else:
                    cls._connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")
    
    @classmethod
    def execute_query(cls, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """Execute query with connection pool management and retry logic"""
        max_retries = 2
        
        for attempt in range(max_retries):
            conn = None
            cursor = None
            connection_failed = False
            
            try:
                conn = cls.get_connection()
                if not conn:
                    logger.error(f"Failed to get connection on attempt {attempt + 1}")
                    continue
                    
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cursor.execute(query, params)
                
                # Check if this is a SELECT query that should return results
                query_upper = query.strip().upper()
                is_select_query = query_upper.startswith('SELECT') or 'RETURNING' in query_upper
                
                if is_select_query:
                    if fetch_one:
                        result = cursor.fetchone()
                    elif fetch_all:
                        result = cursor.fetchall()
                    else:
                        result = None
                else:
                    # For UPDATE, DELETE, INSERT without RETURNING, return rowcount
                    result = cursor.rowcount
                    
                conn.commit()
                return result
                
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Connection-related errors - retry with new connection
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                connection_failed = True
                if conn:
                    conn.rollback()
                    
            except Exception as e:
                # Other errors - don't retry
                logger.error(f"Query execution failed: {e}")
                if conn:
                    conn.rollback()
                return None
                
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if conn:
                    cls.return_connection(conn, close_conn=connection_failed)
                    
        logger.error(f"Query failed after {max_retries} attempts")
        return None

class CartService:
    """Service for cart-related database operations"""
    
    @staticmethod
    def get_cart_items(user_custom_id: str) -> List[Dict]:
        """Get all cart items for a user with product details using custom_id"""
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
            WHERE ci.user_custom_id = %s
            ORDER BY p.name, pv.variation_name
        """
        result = DatabaseService.execute_query(query, (user_custom_id,))
        return result if result else []
    
    @staticmethod
    def add_to_cart(user_custom_id: str, variation_id: int) -> Optional[int]:
        """Add item to cart or update quantity using UPSERT with custom_id"""
        query = """
            INSERT INTO cart_items (user_custom_id, variation_id, quantity)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_custom_id, variation_id)
            DO UPDATE SET quantity = cart_items.quantity + 1
            RETURNING quantity
        """
        result = DatabaseService.execute_query(query, (user_custom_id, variation_id), fetch_one=True)
        return result[0] if result else None
    
    @staticmethod
    def update_cart_quantity(user_custom_id: str, variation_id: int, action: str) -> Optional[int]:
        """Update cart item quantity (increment or decrement) using custom_id"""
        if action == 'incr':
            query = """
                UPDATE cart_items 
                SET quantity = quantity + 1 
                WHERE user_custom_id = %s AND variation_id = %s
                RETURNING quantity
            """
        elif action == 'decr':
            query = """
                UPDATE cart_items 
                SET quantity = quantity - 1 
                WHERE user_custom_id = %s AND variation_id = %s
                RETURNING quantity
            """
        else:
            return None
            
        result = DatabaseService.execute_query(query, (user_custom_id, variation_id), fetch_one=True)
        return result[0] if result else None
    
    @staticmethod
    def remove_cart_item(user_custom_id: str, variation_id: int) -> bool:
        """Remove item from cart using custom_id"""
        query = """
            DELETE FROM cart_items 
            WHERE user_custom_id = %s AND variation_id = %s
        """
        result = DatabaseService.execute_query(query, (user_custom_id, variation_id), fetch_all=False)
        return result is not None
    
    @staticmethod
    def get_cart_item_details(user_custom_id: str, variation_id: int) -> Optional[Dict]:
        """Get single cart item details using custom_id"""
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
            WHERE ci.user_custom_id = %s AND ci.variation_id = %s
        """
        result = DatabaseService.execute_query(query, (user_custom_id, variation_id), fetch_one=True)
        return dict(result) if result else None

class UserService:
    """Service for user-related database operations using encrypted phone storage"""
    
    @staticmethod
    def find_user_by_phone(phone: str) -> Optional['User']:
        """Find user by phone number using encrypted phone hash"""
        from models import User
        from utils.encryption import DataEncryption
        
        # Create hash of the phone number for lookup
        phone_hash = DataEncryption.hash_for_search(phone)
        user = User.query.filter_by(phone_hash=phone_hash, is_active=True).first()
        return user
    
    @staticmethod
    def create_user(phone: str, first_name: str = "User", last_name: str = "") -> Optional['User']:
        """Create new user with phone number using encrypted storage and custom_id"""
        from models import User, db
        from utils.id_generator import CustomIDGenerator
        try:
            # Generate default values if not provided
            if not last_name:
                last_name = phone[-4:]
            
            # Generate custom_id
            custom_id = CustomIDGenerator.generate_user_id()
                
            user = User(
                first_name=first_name,
                last_name=last_name,
                custom_id=custom_id
            )
            # Use the set_phone method which handles encryption
            user.set_phone(phone)
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Created new user with custom_id: {custom_id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def find_user_by_id(user_id: int) -> Optional['User']:
        """Find user by ID"""
        from models import User
        return User.query.filter_by(id=user_id, is_active=True).first()

class AddressService:
    """Service for address-related database operations"""
    
    @staticmethod
    def get_user_addresses(user_custom_id: str) -> List[Dict]:
        """Get all addresses for a user using custom_id"""
        query = """
            SELECT 
                id, nickname, house_number_encrypted, block_name, floor_door_encrypted, 
                contact_number_encrypted, latitude, longitude, locality, city, 
                pincode, nearby_landmark_encrypted, address_notes, is_default,
                created_at, updated_at
            FROM addresses
            WHERE user_custom_id = %s
            ORDER BY is_default DESC, created_at DESC
        """
        result = DatabaseService.execute_query(query, (user_custom_id,))
        return result if result else []
    
    @staticmethod
    def get_default_address(user_custom_id: str) -> Optional[Dict]:
        """Get default address for a user using custom_id"""
        query = """
            SELECT 
                id, nickname, house_number_encrypted, block_name, floor_door_encrypted, 
                contact_number_encrypted, latitude, longitude, locality, city, 
                pincode, nearby_landmark_encrypted, address_notes, is_default,
                created_at, updated_at
            FROM addresses
            WHERE user_custom_id = %s AND is_default = true
            LIMIT 1
        """
        result = DatabaseService.execute_query(query, (user_custom_id,), fetch_one=True)
        return dict(result) if result else None
    
    @staticmethod
    def create_address(user_custom_id: str, address_data: Dict) -> Optional[int]:
        """Create a new address for a user using custom_id"""
        query = """
            INSERT INTO addresses (
                user_custom_id, nickname, house_number_encrypted, block_name, floor_door_encrypted,
                contact_number_encrypted, latitude, longitude, locality, city, 
                pincode, nearby_landmark_encrypted, address_notes, is_default,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING id
        """
        
        # If this is set as default, first unset all other defaults
        if address_data.get('is_default', False):
            AddressService.unset_default_address(user_custom_id)
        
        result = DatabaseService.execute_query(query, (
            user_custom_id,
            address_data['nickname'],
            address_data['house_number'],
            address_data.get('block_name', ''),
            address_data['floor_door'],
            address_data['contact_number'],
            address_data['latitude'],
            address_data['longitude'],
            address_data['locality'],
            address_data['city'],
            address_data['pincode'],
            address_data.get('nearby_landmark', ''),
            address_data.get('address_notes', ''),
            address_data.get('is_default', False)
        ), fetch_one=True)
        
        return result[0] if result else None
    
    @staticmethod
    def update_address(address_id: int, user_custom_id: str, address_data: Dict) -> bool:
        """Update an existing address using custom_id"""
        query = """
            UPDATE addresses SET
                nickname = %s, house_number = %s, block_name = %s, floor_door = %s,
                contact_number = %s, latitude = %s, longitude = %s, locality = %s, 
                city = %s, pincode = %s, nearby_landmark = %s, address_notes = %s,
                is_default = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_custom_id = %s
        """
        
        # If this is set as default, first unset all other defaults
        if address_data.get('is_default', False):
            AddressService.unset_default_address(user_custom_id)
        
        result = DatabaseService.execute_query(query, (
            address_data['nickname'],
            address_data['house_number'],
            address_data.get('block_name', ''),
            address_data['floor_door'],
            address_data['contact_number'],
            address_data['latitude'],
            address_data['longitude'],
            address_data['locality'],
            address_data['city'],
            address_data['pincode'],
            address_data.get('nearby_landmark', ''),
            address_data.get('address_notes', ''),
            address_data.get('is_default', False),
            address_id,
            user_custom_id
        ), fetch_all=False)
        
        return result is not None
    
    @staticmethod
    def delete_address(address_id: int, user_custom_id: str) -> bool:
        """Delete an address using custom_id"""
        query = """
            DELETE FROM addresses 
            WHERE id = %s AND user_custom_id = %s
        """
        result = DatabaseService.execute_query(query, (address_id, user_custom_id), fetch_all=False)
        return result is not None
    
    @staticmethod
    def unset_default_address(user_custom_id: str) -> bool:
        """Unset default flag for all addresses of a user using custom_id"""
        query = """
            UPDATE addresses SET is_default = false 
            WHERE user_custom_id = %s AND is_default = true
        """
        result = DatabaseService.execute_query(query, (user_custom_id,), fetch_all=False)
        return result is not None
    
    @staticmethod
    def set_default_address(address_id: int, user_custom_id: str) -> bool:
        """Set an address as default using custom_id"""
        # First unset all defaults
        AddressService.unset_default_address(user_custom_id)
        
        # Then set the new default
        query = """
            UPDATE addresses SET is_default = true, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_custom_id = %s
        """
        result = DatabaseService.execute_query(query, (address_id, user_custom_id), fetch_all=False)
        return result is not None
    
    @staticmethod
    def get_address_by_id(address_id: int, user_custom_id: str) -> Optional[Dict]:
        """Get a specific address by ID using custom_id"""
        query = """
            SELECT 
                id, nickname, house_number, block_name, floor_door, 
                contact_number, latitude, longitude, locality, city, 
                pincode, nearby_landmark, address_notes, is_default,
                created_at, updated_at
            FROM addresses
            WHERE id = %s AND user_custom_id = %s
        """
        result = DatabaseService.execute_query(query, (address_id, user_custom_id), fetch_one=True)
        return dict(result) if result else None