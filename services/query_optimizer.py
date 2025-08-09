"""
Query optimization service for Monthly Organics
Contains optimized database queries for better performance
"""
from typing import Dict, List, Optional
from .database import DatabaseService

class QueryOptimizer:
    """Optimized database queries for common operations"""
    
    @staticmethod
    def get_cart_summary(user_custom_id: str) -> Dict:
        """Get cart summary with totals in single query using custom_id"""
        query = """
            SELECT 
                COUNT(*) as item_count,
                SUM(ci.quantity) as total_quantity,
                SUM(ci.quantity * pv.mrp) as subtotal
            FROM cart_items ci
            INNER JOIN product_variations pv ON ci.variation_id = pv.id
            WHERE ci.user_custom_id = %s
        """
        result = DatabaseService.execute_query(query, (user_custom_id,), fetch_one=True)
        
        if result:
            return {
                'item_count': result['item_count'] or 0,
                'total_quantity': result['total_quantity'] or 0,
                'subtotal': float(result['subtotal'] or 0)
            }
        return {'item_count': 0, 'total_quantity': 0, 'subtotal': 0.0}
    
    @staticmethod
    def get_user_with_default_address(user_custom_id: str) -> Optional[Dict]:
        """Get user with their default address in single query using custom_id"""
        query = """
            SELECT 
                u.id as user_id,
                u.custom_id,
                u.first_name,
                u.last_name,
                u.phone_encrypted,
                a.id as address_id,
                a.nickname,
                a.house_number_encrypted,
                a.locality,
                a.city,
                a.pincode
            FROM users u
            LEFT JOIN addresses a ON u.custom_id = a.user_custom_id AND a.is_default = true
            WHERE u.custom_id = %s
        """
        return DatabaseService.execute_query(query, (user_custom_id,), fetch_one=True)
    
    @staticmethod
    def get_products_with_cart_quantities(user_custom_id: str, category_id: Optional[int] = None) -> List[Dict]:
        """Get products with cart quantities in single optimized query using custom_id"""
        base_query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                p.description,
                p.category_id,
                p.is_best_seller,
                pv.id as variation_id,
                pv.variation_name,
                pv.mrp,
                pv.stock_quantity,
                COALESCE(ci.quantity, 0) as cart_quantity,
                c.name as category_name
            FROM products p
            LEFT JOIN product_variations pv ON p.id = pv.product_id
            LEFT JOIN cart_items ci ON pv.id = ci.variation_id AND ci.user_custom_id = %s
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id IS NOT NULL
        """
        
        params = [user_custom_id]
        
        if category_id:
            base_query += " AND p.category_id = %s"
            params.append(str(category_id))
        
        base_query += " ORDER BY c.name, p.name, pv.variation_name"
        
        return DatabaseService.execute_query(base_query, tuple(params)) or []