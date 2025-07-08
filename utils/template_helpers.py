"""
Template rendering helpers for Monthly Organics
Separates HTML generation from route logic
"""
from flask import render_template_string

def render_cart_item(item_data: dict) -> str:
    """Render cart item HTML from template"""
    template = '''
    <div class="cart-item-wrapper border-b border-gray-100 p-4 last:border-b-0">
        <div class="flex items-start space-x-3">
            <!-- Product Image Placeholder -->
            <div class="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
            </div>
            
            <!-- Product Details -->
            <div class="flex-1 min-w-0">
                <h3 class="font-medium text-gray-900 text-sm">{{ product_name }}</h3>
                <p class="text-sm text-gray-600">{{ variation_name }}</p>
                
                <div class="flex items-center justify-between mt-2">
                    <!-- Quantity Controls -->
                    <div class="flex items-center space-x-2 bg-gray-50 rounded-lg px-2 py-1">
                        <button hx-post="/update-cart/{{ variation_id }}/decr" 
                                hx-target="closest .cart-item-wrapper"
                                hx-swap="outerHTML"
                                hx-trigger="click"
                                onclick="window.updateCartTotalsReliable();"
                                class="w-7 h-7 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors text-sm">
                            -
                        </button>
                        <span class="px-2 font-medium text-gray-800 min-w-[24px] text-center">{{ quantity }}</span>
                        <button hx-post="/update-cart/{{ variation_id }}/incr" 
                                hx-target="closest .cart-item-wrapper"
                                hx-swap="outerHTML"
                                hx-trigger="click"
                                onclick="window.updateCartTotalsReliable();"
                                class="w-7 h-7 bg-green-500 text-white rounded-full flex items-center justify-center hover:bg-green-600 transition-colors text-sm">
                            +
                        </button>
                    </div>
                    
                    <!-- Price -->
                    <div class="text-right">
                        <p class="text-sm font-medium text-gray-900">₹{{ "%.2f"|format(total_price) }}</p>
                        <p class="text-xs text-gray-500">₹{{ "%.2f"|format(price) }} each</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    return render_template_string(template, **item_data)

def render_store_quantity_stepper(variation_id: int, quantity: int) -> str:
    """Render store page quantity stepper"""
    template = '''
    <div class="flex items-center space-x-2 bg-green-100 border border-green-300 rounded-lg px-3 py-1">
        <button hx-post="/update-cart/{{ variation_id }}/decr" 
                hx-target="closest div"
                hx-swap="outerHTML"
                class="w-8 h-8 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors">
            -
        </button>
        <span class="px-2 font-semibold text-green-800">{{ quantity }}</span>
        <button hx-post="/update-cart/{{ variation_id }}/incr" 
                hx-target="closest div"
                hx-swap="outerHTML"
                class="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center hover:bg-green-600 transition-colors">
            +
        </button>
    </div>
    '''
    return render_template_string(template, variation_id=variation_id, quantity=quantity)

def render_add_to_cart_button(variation_id: int) -> str:
    """Render add to cart button for store page"""
    template = '''
    <button hx-post="/add-to-cart/{{ variation_id }}" 
            hx-swap="outerHTML"
            class="bg-green-600 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500/20">
        Add to Cart
    </button>
    '''
    return render_template_string(template, variation_id=variation_id)

def render_cart_totals(subtotal: float, delivery_fee: float, total: float) -> str:
    """Render cart totals section"""
    template = '''
    <div class="space-y-2" id="order-totals">
        <div class="flex justify-between text-sm">
            <span class="text-gray-600">Subtotal</span>
            <span class="text-gray-900">₹{{ "%.2f"|format(subtotal) }}</span>
        </div>
        
        <div class="flex justify-between text-sm">
            <span class="text-gray-600">Delivery Fee</span>
            <span class="text-gray-900">₹{{ "%.2f"|format(delivery_fee) }}</span>
        </div>
        
        <div class="border-t border-gray-200 pt-2 mt-2">
            <div class="flex justify-between font-medium">
                <span class="text-gray-900">Total</span>
                <span class="text-green-600 text-lg font-bold">₹{{ "%.2f"|format(total) }}</span>
            </div>
        </div>
    </div>
    '''
    return render_template_string(template, subtotal=subtotal, delivery_fee=delivery_fee, total=total)