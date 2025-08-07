"""
Store routes for Monthly Organics
Handles product display and category navigation
"""
import logging
from services.database import DatabaseService

logger = logging.getLogger(__name__)

def store():
    """Store page route that displays categories and products."""
    try:
        query = """
            SELECT id, name, icon_url 
            FROM categories 
            ORDER BY name
        """
        categories = DatabaseService.execute_query(query)
        
        # Get all products with their variations
        query = """
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
                c.name as category_name
            FROM products p
            LEFT JOIN product_variations pv ON p.id = pv.product_id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.category_id IS NOT NULL
            ORDER BY c.name, p.name, pv.variation_name
        """
        products_data = DatabaseService.execute_query(query)
        
        from flask import render_template
        return render_template('store.html', 
                             categories=categories or [],
                             products_data=products_data or [])
        
    except Exception as e:
        logger.error(f"Error loading store page: {e}")
        from flask import render_template
        return render_template('store.html', categories=[], products_data=[])

def products_by_category(category_id):
    """HTMX route that returns products for a specific category."""
    try:
        from flask import session
        
        # Get user cart items if logged in using custom_id
        user_cart = {}
        if 'user_custom_id' in session:
            user_custom_id = session['user_custom_id']
            cart_query = """
                SELECT variation_id, quantity 
                FROM cart_items 
                WHERE user_custom_id = %s
            """
            cart_items = DatabaseService.execute_query(cart_query, (user_custom_id,))
            user_cart = {item['variation_id']: item['quantity'] for item in (cart_items or [])}
        
        query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                p.description,
                p.category_id,
                p.is_best_seller,
                pv.id as variation_id,
                pv.variation_name,
                pv.mrp,
                pv.stock_quantity
            FROM products p
            LEFT JOIN product_variations pv ON p.id = pv.product_id
            WHERE p.category_id = %s
            ORDER BY p.name, pv.variation_name
        """
        raw_products = DatabaseService.execute_query(query, (category_id,))
        
        # Group products with their variations
        products = {}
        for row in (raw_products or []):
            prod_id = row['product_id']
            if prod_id not in products:
                products[prod_id] = {
                    'id': prod_id,
                    'name': row['product_name'],
                    'description': row['description'],
                    'is_best_seller': row['is_best_seller'],
                    'variations': []
                }
            
            if row['variation_id']:
                variation = {
                    'id': row['variation_id'],
                    'name': row['variation_name'],
                    'price': float(row['mrp']),
                    'stock': row['stock_quantity'] or 0,
                    'cart_quantity': user_cart.get(row['variation_id'], 0)
                }
                products[prod_id]['variations'].append(variation)
        
        products_list = list(products.values())
        
        from flask import render_template
        return render_template('partials/product_list.html', products=products_list)
        
    except Exception as e:
        logger.error(f"Error loading products for category {category_id}: {e}")
        return '<div class="text-center text-gray-500 py-8">Error loading products</div>'

def all_products():
    """Route that returns all products grouped by categories for the store page.""" 
    try:
        from flask import session
        
        # Cart quantities are now included in the main query above for better performance
        
        # Optimized single query to get all data including cart quantities
        query = """
            SELECT 
                c.id as category_id,
                c.name as category_name,
                p.id as product_id,
                p.name as product_name,
                p.description,
                p.is_best_seller,
                pv.id as variation_id,
                pv.variation_name,
                pv.mrp,
                pv.stock_quantity,
                COALESCE(ci.quantity, 0) as cart_quantity
            FROM categories c
            LEFT JOIN products p ON c.id = p.category_id
            LEFT JOIN product_variations pv ON p.id = pv.product_id
            LEFT JOIN cart_items ci ON pv.id = ci.variation_id AND ci.user_custom_id = %s
            WHERE p.id IS NOT NULL
            ORDER BY c.name, p.name, pv.variation_name
        """
        
        # Get user custom_id directly from session for cart operations
        user_custom_id = session.get('user_custom_id')
        
        raw_data = DatabaseService.execute_query(query, (user_custom_id or '',))
        
        # Group data by categories and products
        categories_with_products = {}
        
        for row in (raw_data or []):
            cat_id = row['category_id']
            cat_name = row['category_name']
            prod_id = row['product_id']
            
            # Initialize category if not exists
            if cat_id not in categories_with_products:
                categories_with_products[cat_id] = {
                    'id': cat_id,
                    'name': cat_name,
                    'products': {}
                }
            
            # Initialize product if not exists
            if prod_id not in categories_with_products[cat_id]['products']:
                categories_with_products[cat_id]['products'][prod_id] = {
                    'id': prod_id,
                    'name': row['product_name'],
                    'description': row['description'],
                    'is_best_seller': row['is_best_seller'],
                    'variations': []
                }
            
            # Add variation if it exists
            if row['variation_id']:
                variation = {
                    'id': row['variation_id'],
                    'name': row['variation_name'],
                    'price': float(row['mrp']),
                    'stock': row['stock_quantity'] or 0,
                    'cart_quantity': row['cart_quantity']
                }
                categories_with_products[cat_id]['products'][prod_id]['variations'].append(variation)
        
        # Convert to list format expected by template
        final_categories = []
        for cat_data in categories_with_products.values():
            if cat_data['products']:  # Only include categories with products
                cat_data['products'] = list(cat_data['products'].values())
                final_categories.append(cat_data)
        
        from flask import render_template
        return render_template('partials/all_products.html', categories_with_products=final_categories)
        
    except Exception as e:
        logger.error(f"Error loading all products: {e}")
        return '<div class="text-center text-gray-500 py-8">Error loading products</div>'