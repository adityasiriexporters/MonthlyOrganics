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
        products = DatabaseService.execute_query(query, (category_id,))
        
        from flask import render_template
        return render_template('partials/product_list.html', products=products or [])
        
    except Exception as e:
        logger.error(f"Error loading products for category {category_id}: {e}")
        return '<div class="text-center text-gray-500 py-8">Error loading products</div>'

def all_products():
    """Route that returns all products grouped by categories for the store page.""" 
    try:
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
        return render_template('partials/all_products.html', products_data=products_data or [])
        
    except Exception as e:
        logger.error(f"Error loading all products: {e}")
        return '<div class="text-center text-gray-500 py-8">Error loading products</div>'