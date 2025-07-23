"""
Service for handling delivery zone operations and spatial queries
"""
import logging
from datetime import date, timedelta
from services.database import DatabaseService
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class DeliveryZoneService:
    """Service for delivery zone operations and spatial queries"""
    
    @staticmethod
    def check_address_in_delivery_zone(latitude: float, longitude: float) -> Optional[Dict]:
        """
        Check if the given coordinates fall within any delivery zone.
        Returns zone info with free dates if found, None otherwise.
        """
        try:
            # Spatial query to find zones containing the point
            # Use ST_SetSRID to ensure both geometries use the same coordinate system (4326 = WGS84)
            spatial_query = """
                SELECT dz.id, dz.name, dz.geojson
                FROM delivery_zones dz
                WHERE ST_Contains(dz.geometry, ST_SetSRID(ST_Point(%s, %s), 4326))
                LIMIT 1
            """
            
            zone_result = DatabaseService.execute_query(
                spatial_query, 
                (longitude, latitude),  # PostGIS uses (longitude, latitude) order
                fetch_one=True
            )
            
            if not zone_result:
                logger.info(f"Address at ({latitude}, {longitude}) is not in any delivery zone")
                return None
            
            # Get upcoming free delivery dates for this zone
            free_dates_query = """
                SELECT free_date
                FROM delivery_zone_free_dates
                WHERE zone_id = %s AND free_date >= CURRENT_DATE
                ORDER BY free_date ASC
            """
            
            free_dates_result = DatabaseService.execute_query(
                free_dates_query,
                (zone_result['id'],),
                fetch_all=True
            )
            
            free_dates = [row['free_date'] for row in free_dates_result] if free_dates_result else []
            
            logger.info(f"Address in zone '{zone_result['name']}' with {len(free_dates)} free dates")
            
            return {
                'zone_id': zone_result['id'],
                'zone_name': zone_result['name'],
                'free_dates': free_dates
            }
            
        except Exception as e:
            logger.error(f"Error checking delivery zone: {e}")
            return None
    
    @staticmethod
    def get_shipping_options(latitude: float, longitude: float, order_total: float) -> List[Dict]:
        """
        Get available shipping options based on location and order total.
        Returns list of shipping options with pricing and delivery dates.
        """
        try:
            shipping_options = []
            
            # Check if address is in a delivery zone
            zone_info = DeliveryZoneService.check_address_in_delivery_zone(latitude, longitude)
            
            if zone_info and zone_info['free_dates']:
                # Address is in zone with free delivery dates
                next_free_date = zone_info['free_dates'][0]
                
                # Add free delivery option as default
                shipping_options.append({
                    'id': 'free_delivery',
                    'name': 'Free Delivery',
                    'price': 0.00,
                    'delivery_date': next_free_date,
                    'is_default': True,
                    'is_free': True,
                    'estimated_days': (next_free_date - date.today()).days
                })
            
            # Add standard paid shipping options (hardcoded examples as requested)
            today = date.today()
            
            # Standard shipping options with varying prices and delivery times
            standard_options = [
                {
                    'id': 'blue_dart',
                    'name': 'Blue Dart Express',
                    'price': 90.00,
                    'delivery_date': today + timedelta(days=1),
                    'estimated_days': 1
                },
                {
                    'id': 'delhivery',
                    'name': 'Delhivery Standard',
                    'price': 120.00,
                    'delivery_date': today + timedelta(days=5),
                    'estimated_days': 5
                },
                {
                    'id': 'dhl',
                    'name': 'DHL Economy',
                    'price': 50.00,
                    'delivery_date': today + timedelta(days=8),
                    'estimated_days': 8
                }
            ]
            
            # Add paid options
            for i, option in enumerate(standard_options):
                option['is_default'] = False if zone_info and zone_info['free_dates'] else (i == 0)
                option['is_free'] = False
                shipping_options.append(option)
            
            # If no free delivery and no zone match, make first paid option default
            if not any(opt['is_default'] for opt in shipping_options) and shipping_options:
                shipping_options[0]['is_default'] = True
            
            logger.info(f"Generated {len(shipping_options)} shipping options for location")
            return shipping_options
            
        except Exception as e:
            logger.error(f"Error getting shipping options: {e}")
            # Return basic options in case of error
            return [
                {
                    'id': 'standard',
                    'name': 'Standard Delivery',
                    'price': 60.00,
                    'delivery_date': date.today() + timedelta(days=3),
                    'is_default': True,
                    'is_free': False,
                    'estimated_days': 3
                }
            ]
    
    @staticmethod
    def calculate_delivery_fee(shipping_option_id: str, latitude: float, longitude: float, order_total: float) -> Tuple[float, Dict]:
        """
        Calculate delivery fee based on selected shipping option.
        Returns (delivery_fee, shipping_option_details)
        """
        try:
            shipping_options = DeliveryZoneService.get_shipping_options(latitude, longitude, order_total)
            
            # Find selected option
            selected_option = None
            for option in shipping_options:
                if option['id'] == shipping_option_id:
                    selected_option = option
                    break
            
            if not selected_option:
                # Default to first option if not found
                selected_option = shipping_options[0] if shipping_options else {
                    'id': 'standard',
                    'name': 'Standard Delivery',
                    'price': 60.00,
                    'is_free': False
                }
            
            delivery_fee = selected_option['price']
            
            return delivery_fee, selected_option
            
        except Exception as e:
            logger.error(f"Error calculating delivery fee: {e}")
            return 60.00, {'id': 'standard', 'name': 'Standard Delivery', 'price': 60.00, 'is_free': False}