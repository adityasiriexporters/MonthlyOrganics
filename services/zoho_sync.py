"""
Zoho Inventory Synchronization Service

This module handles synchronization between local products/orders 
and Zoho Inventory items/sales orders.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from services.database import DatabaseService
from services.zoho_inventory import ZohoInventoryAPI, ZohoAPIError, ZohoOAuthError

logger = logging.getLogger(__name__)

class ZohoSyncService:
    """
    Service for synchronizing data between local system and Zoho Inventory
    """
    
    def __init__(self):
        self.zoho_api = ZohoInventoryAPI()
    
    def is_zoho_connected(self) -> bool:
        """Check if Zoho is properly connected and authenticated"""
        try:
            return self.zoho_api.is_authenticated()
        except Exception as e:
            logger.error(f"Error checking Zoho connection: {e}")
            return False
    
    def sync_products_to_zoho(self) -> Dict[str, int]:
        """
        Sync local products to Zoho Inventory as items
        Returns dict with counts: {'created': 0, 'updated': 0, 'errors': 0}
        """
        results = {'created': 0, 'updated': 0, 'errors': 0}
        
        if not self.is_zoho_connected():
            logger.error("Zoho not connected - cannot sync products")
            return results
        
        try:
            # Get all local products that need syncing
            query = """
                SELECT p.id, p.name, p.description, p.category_id, p.is_active,
                       zm.zoho_item_id, zm.sync_status
                FROM products p
                LEFT JOIN zoho_item_mappings zm ON p.id = zm.local_product_id
                WHERE p.is_active = true
                ORDER BY p.id
            """
            products = DatabaseService.execute_query(query)
            
            for product in products:
                try:
                    if product.get('zoho_item_id'):  # Has existing zoho_item_id
                        # Update existing item
                        success = self._update_zoho_item(product)
                        if success:
                            results['updated'] += 1
                        else:
                            results['errors'] += 1
                    else:
                        # Create new item
                        success = self._create_zoho_item(product)
                        if success:
                            results['created'] += 1
                        else:
                            results['errors'] += 1
                            
                except Exception as e:
                    logger.error(f"Error syncing product {product['id']}: {e}")
                    results['errors'] += 1
            
            logger.info(f"Product sync completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during product sync: {e}")
            results['errors'] = -1
            return results
    
    def _create_zoho_item(self, product) -> bool:
        """Create a new item in Zoho Inventory"""
        try:
            # Prepare item data for Zoho
            item_data = {
                'name': product.get('name', ''),
                'description': product.get('description', ''),
                'item_type': 'inventory',
                'product_type': 'goods',
                'status': 'active' if product.get('is_active') else 'inactive',
                'initial_stock': 0,
                'initial_stock_rate': 0.0
            }
            
            # Add category if available
            if product.get('category_id'):
                category_name = self._get_category_name(product['category_id'])
                if category_name:
                    item_data['category_name'] = category_name
            
            # Create item in Zoho
            response = self.zoho_api.create_item(item_data)
            
            if response.get('code') == 0:  # Success
                zoho_item = response.get('item', {})
                zoho_item_id = zoho_item.get('item_id')
                zoho_item_name = zoho_item.get('name')
                
                if zoho_item_id:
                    # Save mapping to database
                    self._save_item_mapping(product['id'], zoho_item_id, zoho_item_name, 'synced')
                    logger.info(f"Created Zoho item {zoho_item_id} for product {product['id']}")
                    return True
            
            logger.error(f"Failed to create Zoho item for product {product['id']}: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating Zoho item for product {product['id']}: {e}")
            return False
    
    def _update_zoho_item(self, product) -> bool:
        """Update existing item in Zoho Inventory"""
        try:
            zoho_item_id = product.get('zoho_item_id')
            
            # Prepare update data
            item_data = {
                'name': product.get('name', ''),
                'description': product.get('description', ''),
                'status': 'active' if product.get('is_active') else 'inactive'
            }
            
            # Add category if available
            if product.get('category_id'):
                category_name = self._get_category_name(product['category_id'])
                if category_name:
                    item_data['category_name'] = category_name
            
            # Update item in Zoho
            response = self.zoho_api.update_item(zoho_item_id, item_data)
            
            if response.get('code') == 0:  # Success
                # Update mapping status
                self._update_mapping_status(product['id'], 'synced')
                logger.info(f"Updated Zoho item {zoho_item_id} for product {product['id']}")
                return True
            
            logger.error(f"Failed to update Zoho item {zoho_item_id} for product {product['id']}: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating Zoho item for product {product['id']}: {e}")
            return False
    
    def sync_products_from_zoho(self) -> Dict[str, int]:
        """
        Import items from Zoho Inventory as local products
        Returns dict with counts: {'imported': 0, 'errors': 0}
        """
        results = {'imported': 0, 'errors': 0}
        
        if not self.is_zoho_connected():
            logger.error("Zoho not connected - cannot import products")
            return results
        
        try:
            # Get all items from Zoho
            page = 1
            while True:
                response = self.zoho_api.get_items(page=page, per_page=200)
                
                if response.get('code') != 0:
                    logger.error(f"Failed to fetch Zoho items: {response}")
                    break
                
                items = response.get('items', [])
                if not items:
                    break
                
                for item in items:
                    try:
                        success = self._import_zoho_item(item)
                        if success:
                            results['imported'] += 1
                        else:
                            results['errors'] += 1
                    except Exception as e:
                        logger.error(f"Error importing Zoho item {item.get('item_id')}: {e}")
                        results['errors'] += 1
                
                # Check if there are more pages
                if len(items) < 200:
                    break
                page += 1
            
            logger.info(f"Zoho import completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during Zoho import: {e}")
            results['errors'] = -1
            return results
    
    def _import_zoho_item(self, item: Dict) -> bool:
        """Import a single item from Zoho as a local product"""
        try:
            zoho_item_id = item.get('item_id')
            zoho_item_name = item.get('name')
            
            if not zoho_item_id or not zoho_item_name:
                logger.warning(f"Invalid Zoho item data: {item}")
                return False
            
            # Check if mapping already exists
            check_query = """
                SELECT local_product_id FROM zoho_item_mappings 
                WHERE zoho_item_id = %s
            """
            existing = DatabaseService.execute_query(check_query, (zoho_item_id,), fetch_one=True)
            
            if existing:
                logger.info(f"Zoho item {zoho_item_id} already mapped to product {existing['local_product_id']}")
                return True
            
            # Create new product
            create_query = """
                INSERT INTO products (name, description, category_id, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            product_result = DatabaseService.execute_query(create_query, (
                zoho_item_name,
                item.get('description', ''),
                1,  # Default category
                item.get('status') == 'active',
                datetime.utcnow()
            ), fetch_one=True)
            
            if product_result:
                product_id = product_result['id']
                
                # Create mapping
                mapping_query = """
                    INSERT INTO zoho_item_mappings 
                    (local_product_id, zoho_item_id, zoho_item_name, sync_status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                DatabaseService.execute_query(mapping_query, (
                    product_id, zoho_item_id, zoho_item_name, 'synced',
                    datetime.utcnow(), datetime.utcnow()
                ), fetch_all=False)
                
                logger.info(f"Imported Zoho item {zoho_item_id} as product {product_id}")
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Error importing Zoho item {item.get('item_id', 'unknown')}: {e}")
            return False
    
    def create_sales_order_in_zoho(self, local_order_id: int) -> bool:
        """
        Create a sales order in Zoho Inventory from a local order
        """
        if not self.is_zoho_connected():
            logger.error("Zoho not connected - cannot create sales order")
            return False
        
        try:
            # Get order details
            order_data = self._get_local_order_data(local_order_id)
            if not order_data:
                logger.error(f"Could not find local order {local_order_id}")
                return False
            
            # Convert to Zoho sales order format
            zoho_order_data = self._convert_to_zoho_sales_order(order_data)
            
            # Create sales order in Zoho
            response = self.zoho_api.create_sales_order(zoho_order_data)
            
            if response.get('code') == 0:  # Success
                salesorder = response.get('salesorder', {})
                zoho_so_id = salesorder.get('salesorder_id')
                zoho_so_number = salesorder.get('salesorder_number')
                
                if zoho_so_id:
                    # Save mapping
                    self._save_sales_order_mapping(local_order_id, zoho_so_id, zoho_so_number, 'synced')
                    logger.info(f"Created Zoho sales order {zoho_so_number} for local order {local_order_id}")
                    return True
            
            logger.error(f"Failed to create Zoho sales order for order {local_order_id}: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating Zoho sales order for order {local_order_id}: {e}")
            return False
    
    def _get_local_order_data(self, order_id: int) -> Optional[Dict]:
        """Get local order data with items"""
        try:
            # Get order details (this query would need to be adjusted based on your actual order schema)
            order_query = """
                SELECT o.id, o.user_custom_id, o.total_amount, o.delivery_address, 
                       o.created_at, u.first_name, u.last_name, u.phone_encrypted
                FROM orders o
                JOIN users u ON o.user_custom_id = u.custom_id
                WHERE o.id = %s
            """
            order = DatabaseService.execute_query(order_query, (order_id,), fetch_one=True)
            
            if not order:
                return None
            
            # Get order items
            items_query = """
                SELECT oi.product_id, oi.quantity, oi.price, p.name, zm.zoho_item_id
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                LEFT JOIN zoho_item_mappings zm ON p.id = zm.local_product_id
                WHERE oi.order_id = %s
            """
            items = DatabaseService.execute_query(items_query, (order_id,))
            
            return {
                'order': order,
                'items': items
            }
                
        except Exception as e:
            logger.error(f"Error getting order data for order {order_id}: {e}")
            return None
    
    def _convert_to_zoho_sales_order(self, order_data: Dict) -> Dict:
        """Convert local order data to Zoho sales order format"""
        order = order_data['order']
        items = order_data['items']
        
        # Decrypt customer phone for display
        customer_phone = ""
        if order.get('phone_encrypted'):
            try:
                from utils.encryption import DataEncryption
                customer_phone = DataEncryption.decrypt_phone(order['phone_encrypted']) or ""
            except Exception:
                pass
        
        zoho_order = {
            'customer_name': f"{order['first_name']} {order['last_name']}",
            'reference_number': f"MO-{order['id']}",  # Local order ID as reference
            'date': order['created_at'].strftime('%Y-%m-%d'),
            'line_items': []
        }
        
        # Add customer phone if available
        if customer_phone:
            zoho_order['billing_address'] = {
                'phone': customer_phone
            }
        
        # Add line items
        for item in items:
            if item.get('zoho_item_id'):  # Has zoho_item_id mapping
                line_item = {
                    'item_id': item['zoho_item_id'],
                    'quantity': item['quantity'],
                    'rate': float(item['price'])
                }
                zoho_order['line_items'].append(line_item)
            else:
                logger.warning(f"Product {item['product_id']} not mapped to Zoho item, skipping")
        
        return zoho_order
    
    def _get_category_name(self, category_id: int) -> Optional[str]:
        """Get category name by ID"""
        try:
            query = "SELECT name FROM categories WHERE id = %s"
            result = DatabaseService.execute_query(query, (category_id,), fetch_one=True)
            return result['name'] if result else None
        except Exception:
            return None
    
    def _save_item_mapping(self, product_id: int, zoho_item_id: str, zoho_item_name: str, status: str):
        """Save product-to-item mapping"""
        try:
            # Try update first
            update_query = """
                UPDATE zoho_item_mappings 
                SET zoho_item_name = %s, sync_status = %s, last_sync_at = %s, updated_at = %s
                WHERE local_product_id = %s AND zoho_item_id = %s
            """
            result = DatabaseService.execute_query(update_query, (
                zoho_item_name, status, datetime.utcnow(), datetime.utcnow(), product_id, zoho_item_id
            ), fetch_all=False)
            
            # If no update happened, insert new
            if result == 0:
                insert_query = """
                    INSERT INTO zoho_item_mappings 
                    (local_product_id, zoho_item_id, zoho_item_name, sync_status, last_sync_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                DatabaseService.execute_query(insert_query, (
                    product_id, zoho_item_id, zoho_item_name, status, datetime.utcnow(),
                    datetime.utcnow(), datetime.utcnow()
                ), fetch_all=False)
                
        except Exception as e:
            logger.error(f"Error saving item mapping: {e}")
    
    def _update_mapping_status(self, product_id: int, status: str):
        """Update mapping sync status"""
        try:
            query = """
                UPDATE zoho_item_mappings 
                SET sync_status = %s, last_sync_at = %s, updated_at = %s
                WHERE local_product_id = %s
            """
            DatabaseService.execute_query(query, (
                status, datetime.utcnow(), datetime.utcnow(), product_id
            ), fetch_all=False)
        except Exception as e:
            logger.error(f"Error updating mapping status: {e}")
    
    def _save_sales_order_mapping(self, order_id: int, zoho_so_id: str, zoho_so_number: str, status: str):
        """Save sales order mapping"""
        try:
            query = """
                INSERT INTO zoho_sales_orders 
                (local_order_id, zoho_salesorder_id, zoho_salesorder_number, sync_status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            DatabaseService.execute_query(query, (
                order_id, zoho_so_id, zoho_so_number, status, datetime.utcnow(), datetime.utcnow()
            ), fetch_all=False)
        except Exception as e:
            logger.error(f"Error saving sales order mapping: {e}")
    
    def get_sync_status(self) -> Dict:
        """Get overall sync status and statistics"""
        try:
            # Count products and their sync status
            product_query = """
                SELECT 
                    COUNT(p.id) as total_products,
                    COUNT(zm.id) as mapped_products,
                    COUNT(CASE WHEN zm.sync_status = 'synced' THEN 1 END) as synced_products,
                    COUNT(CASE WHEN zm.sync_status = 'error' THEN 1 END) as error_products
                FROM products p
                LEFT JOIN zoho_item_mappings zm ON p.id = zm.local_product_id
                WHERE p.is_active = true
            """
            product_stats = DatabaseService.execute_query(product_query, fetch_one=True)
            
            # Count sales orders and their sync status
            order_query = """
                SELECT 
                    COUNT(*) as total_synced_orders,
                    COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as successful_orders,
                    COUNT(CASE WHEN sync_status = 'error' THEN 1 END) as failed_orders
                FROM zoho_sales_orders
            """
            order_stats = DatabaseService.execute_query(order_query, fetch_one=True)
            
            return {
                'connected': self.is_zoho_connected(),
                'products': {
                    'total': product_stats.get('total_products', 0) if product_stats else 0,
                    'mapped': product_stats.get('mapped_products', 0) if product_stats else 0,
                    'synced': product_stats.get('synced_products', 0) if product_stats else 0,
                    'errors': product_stats.get('error_products', 0) if product_stats else 0
                },
                'orders': {
                    'total_synced': order_stats.get('total_synced_orders', 0) if order_stats else 0,
                    'successful': order_stats.get('successful_orders', 0) if order_stats else 0,
                    'failed': order_stats.get('failed_orders', 0) if order_stats else 0
                }
            }
                
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                'connected': False,
                'products': {'total': 0, 'mapped': 0, 'synced': 0, 'errors': 0},
                'orders': {'total_synced': 0, 'successful': 0, 'failed': 0}
            }