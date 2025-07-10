"""
Store blueprint for Monthly Organics
Handles all store and cart-related routes
"""
import logging
from decimal import Decimal
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from services.database import CartService, DatabaseService
from utils.decorators import login_required
from utils.template_helpers import (
    render_cart_item, render_store_quantity_stepper, 
    render_add_to_cart_button, render_cart_totals
)
from config import Config

logger = logging.getLogger(__name__)

store_bp = Blueprint('store', __name__)


@store_bp.route('/store')
@login_required
def store():
    """Store page route that displays categories and products with search functionality."""
    try:
        search_query = request.args.get('search', '').strip()
        
        # Get categories using optimized query
        categories = _get_categories()
        
        return render_template('store/store.html', 
                             categories=categories, 
                             search_query=search_query)
        
    except Exception as e:
        logger.error(f"Error loading store page: {e}")
        flash('Error loading store page', 'error')
        return redirect(url_for('main.index'))


@store_bp.route('/products/<int:category_id>')
@login_required
def products_by_category(category_id):
    """HTMX route that returns products for a specific category."""
    try:
        user_id = session['user_id']
        
        # Get user cart for quantity display
        user_cart = _get_user_cart(user_id)
        
        # Get products for category
        products = _get_products_by_category(category_id, user_cart)
        
        return render_template('store/partials/product_list.html', products=products)
        
    except Exception as e:
        logger.error(f"Error loading products for category {category_id}: {e}")
        return '<div class="text-center text-gray-500 py-8">Error loading products</div>'


@store_bp.route('/all-products')
@login_required
def all_products():
    """Route that returns all products grouped by categories for the store page."""
    try:
        search_query = request.args.get('search', '').strip()
        user_id = session['user_id']
        
        # Get all products with search and cart data
        categories_with_products = _get_all_products_with_search(user_id, search_query)
        
        # Calculate search results count
        search_results_count = sum(len(cat['products']) for cat in categories_with_products)
        
        return render_template('store/partials/all_products.html', 
                             categories_with_products=categories_with_products,
                             search_query=search_query,
                             search_results_count=search_results_count)
        
    except Exception as e:
        logger.error(f"Error loading all products: {e}")
        return '<div class="text-center text-gray-500 py-8">Error loading products</div>'


@store_bp.route('/cart')
@login_required
def cart():
    """Display user's shopping cart using CartService."""
    try:
        user_id = session['user_id']
        cart_items = CartService.get_cart_items(user_id)
        
        # Calculate totals using business logic
        subtotal = sum(item['total_price'] for item in cart_items)
        delivery_fee = _calculate_delivery_fee(subtotal)
        total = subtotal + delivery_fee
        
        return render_template('store/cart.html', 
                             cart_items=cart_items,
                             subtotal=subtotal,
                             delivery_fee=delivery_fee,
                             total=total)
        
    except Exception as e:
        logger.error(f"Error loading cart: {e}")
        flash('An error occurred while loading your cart. Please try again.', 'error')
        return redirect(url_for('main.index'))


@store_bp.route('/add-to-cart/<int:variation_id>', methods=['POST'])
@login_required
def add_to_cart(variation_id):
    """Add item to cart using CartService."""
    try:
        user_id = session['user_id']
        new_quantity = CartService.add_to_cart(user_id, variation_id)
        
        if new_quantity is None:
            return "Error adding to cart", 500
        
        return render_store_quantity_stepper(variation_id, new_quantity)
        
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return "Error adding to cart", 500


@store_bp.route('/update-cart/<int:variation_id>/<string:action>', methods=['POST'])
@login_required
def update_cart(variation_id, action):
    """Update cart item quantity using CartService and template helpers."""
    try:
        user_id = session['user_id']
        
        if action not in ['incr', 'decr']:
            return "Invalid action", 400
        
        new_quantity = CartService.update_cart_quantity(user_id, variation_id, action)
        
        if new_quantity is None:
            return "Item not found in cart", 404
        
        # Handle quantity zero (remove item)
        if new_quantity <= 0:
            CartService.remove_cart_item(user_id, variation_id)
            return _handle_zero_quantity_response(variation_id)
        
        # Return appropriate response based on page
        return _handle_quantity_update_response(user_id, variation_id, new_quantity)
        
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        return "Error updating cart", 500


@store_bp.route('/cart-totals')
@login_required  
def cart_totals():
    """Return updated cart totals using CartService and template helpers."""
    try:
        user_id = session['user_id']
        cart_items = CartService.get_cart_items(user_id)
        
        subtotal = sum(item['total_price'] for item in cart_items)
        delivery_fee = _calculate_delivery_fee(subtotal)
        total = subtotal + delivery_fee
        
        return render_cart_totals(float(subtotal), float(delivery_fee), float(total))
        
    except Exception as e:
        logger.error(f"Error getting cart totals: {e}")
        return "Error updating totals", 500


# Private helper functions
def _get_categories():
    """Get all categories from database."""
    query = "SELECT id, name FROM categories ORDER BY name"
    categories = DatabaseService.execute_query(query, fetch_all=True)
    return [{'id': cat[0], 'name': cat[1]} for cat in (categories or [])]


def _get_user_cart(user_id):
    """Get user's cart items as dictionary."""
    query = "SELECT variation_id, quantity FROM cart_items WHERE user_id = %s"
    cart_items = DatabaseService.execute_query(query, (user_id,))
    return {item['variation_id']: item['quantity'] for item in (cart_items or [])}


def _get_products_by_category(category_id, user_cart):
    """Get products for a specific category with cart quantities."""
    query = """
        SELECT 
            p.id as product_id, p.name as product_name, p.description, p.is_best_seller,
            pv.id as variation_id, pv.variation_name, pv.mrp, pv.stock_quantity
        FROM products p
        LEFT JOIN product_variations pv ON p.id = pv.product_id
        WHERE p.category_id = %s
        ORDER BY p.name, pv.variation_name
    """
    raw_products = DatabaseService.execute_query(query, (category_id,))
    
    # Group products with variations
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
    
    return list(products.values())


def _get_all_products_with_search(user_id, search_query):
    """Get all products with optional search filtering."""
    base_query = """
        SELECT 
            c.id as category_id, c.name as category_name,
            p.id as product_id, p.name as product_name, p.description, p.is_best_seller,
            pv.id as variation_id, pv.variation_name, pv.mrp, pv.stock_quantity,
            COALESCE(ci.quantity, 0) as cart_quantity
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        LEFT JOIN product_variations pv ON p.id = pv.product_id
        LEFT JOIN cart_items ci ON pv.id = ci.variation_id AND ci.user_id = %s
        WHERE p.id IS NOT NULL
    """
    
    query_params = [user_id]
    
    if search_query:
        base_query += """ AND (
            LOWER(p.name) LIKE LOWER(%s) OR 
            LOWER(p.description) LIKE LOWER(%s) OR 
            LOWER(pv.variation_name) LIKE LOWER(%s) OR
            LOWER(c.name) LIKE LOWER(%s)
        )"""
        search_pattern = f"%{search_query}%"
        query_params.extend([search_pattern] * 4)
    
    base_query += " ORDER BY c.name, p.name, pv.variation_name"
    
    raw_data = DatabaseService.execute_query(base_query, tuple(query_params))
    
    # Group data by categories and products
    categories_with_products = {}
    
    for row in (raw_data or []):
        cat_id = row['category_id']
        prod_id = row['product_id']
        
        # Initialize category
        if cat_id not in categories_with_products:
            categories_with_products[cat_id] = {
                'id': cat_id,
                'name': row['category_name'],
                'products': {}
            }
        
        # Initialize product
        if prod_id not in categories_with_products[cat_id]['products']:
            categories_with_products[cat_id]['products'][prod_id] = {
                'id': prod_id,
                'name': row['product_name'],
                'description': row['description'],
                'is_best_seller': row['is_best_seller'],
                'variations': []
            }
        
        # Add variation
        if row['variation_id']:
            variation = {
                'id': row['variation_id'],
                'name': row['variation_name'],
                'price': float(row['mrp']),
                'stock': row['stock_quantity'] or 0,
                'cart_quantity': row['cart_quantity']
            }
            categories_with_products[cat_id]['products'][prod_id]['variations'].append(variation)
    
    # Convert to list format
    final_categories = []
    for cat_data in categories_with_products.values():
        if cat_data['products']:
            cat_data['products'] = list(cat_data['products'].values())
            final_categories.append(cat_data)
    
    return final_categories


def _calculate_delivery_fee(subtotal):
    """Calculate delivery fee based on business rules."""
    if subtotal >= Config.FREE_DELIVERY_THRESHOLD:
        return Decimal('0.00')
    return Decimal(str(Config.DELIVERY_FEE)) if subtotal > 0 else Decimal('0.00')


def _handle_zero_quantity_response(variation_id):
    """Handle response when quantity becomes zero."""
    referer = request.headers.get('Referer', '')
    if '/store' in referer:
        return render_add_to_cart_button(variation_id)
    return ''


def _handle_quantity_update_response(user_id, variation_id, new_quantity):
    """Handle response for quantity updates."""
    referer = request.headers.get('Referer', '')
    if '/store' in referer:
        return render_store_quantity_stepper(variation_id, new_quantity)
    else:
        # Cart page - return full cart item
        item = CartService.get_cart_item_details(user_id, variation_id)
        return render_cart_item(item) if item else "Item not found"