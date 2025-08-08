"""
Delivery Zone Scheduler Service
Handles automated cleanup of delivery zone free dates
"""

import logging
from datetime import datetime, date, timedelta
from services.database import DatabaseService

logger = logging.getLogger(__name__)

class DeliveryZoneScheduler:
    """Service for managing scheduled delivery zone operations"""
    
    @staticmethod
    def cleanup_expired_free_dates():
        """
        Clean up free delivery dates that are set to occur tomorrow (24 hours before).
        This should be run once daily, preferably during off-peak hours.
        """
        try:
            # Calculate tomorrow's date
            tomorrow = date.today() + timedelta(days=1)
            
            logger.info(f"Starting cleanup of delivery dates for: {tomorrow}")
            
            # Get count of dates to be deleted (for logging)
            count_query = """
                SELECT COUNT(*) as count 
                FROM delivery_zone_free_dates 
                WHERE free_date = %s
            """
            count_result = DatabaseService.execute_query(count_query, (tomorrow,), fetch_one=True)
            dates_to_delete = dict(count_result)['count'] if count_result else 0
            
            if dates_to_delete == 0:
                logger.info("No delivery dates found for cleanup")
                return {'deleted_count': 0, 'status': 'success', 'message': 'No dates to cleanup'}
            
            # Delete the dates
            delete_query = """
                DELETE FROM delivery_zone_free_dates 
                WHERE free_date = %s
            """
            DatabaseService.execute_query(delete_query, (tomorrow,))
            
            logger.info(f"Successfully deleted {dates_to_delete} delivery dates for {tomorrow}")
            
            return {
                'deleted_count': dates_to_delete, 
                'status': 'success', 
                'message': f'Deleted {dates_to_delete} delivery dates for {tomorrow}'
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up delivery dates: {str(e)}", exc_info=True)
            return {
                'deleted_count': 0, 
                'status': 'error', 
                'message': f'Error during cleanup: {str(e)}'
            }
    
    @staticmethod
    def get_upcoming_free_dates(days_ahead=7):
        """
        Get all upcoming free delivery dates within specified days
        Useful for monitoring and reporting
        """
        try:
            end_date = date.today() + timedelta(days=days_ahead)
            
            query = """
                SELECT dz.name as zone_name, df.free_date, 
                       df.free_date - CURRENT_DATE as days_until
                FROM delivery_zone_free_dates df
                JOIN delivery_zones dz ON df.zone_id = dz.id
                WHERE df.free_date BETWEEN CURRENT_DATE AND %s
                ORDER BY df.free_date, dz.name
            """
            
            results = DatabaseService.execute_query(query, (end_date,), fetch_all=True)
            return results or []
            
        except Exception as e:
            logger.error(f"Error getting upcoming free dates: {str(e)}")
            return []
    
    @staticmethod
    def get_zone_statistics():
        """Get statistics about delivery zones and their free dates"""
        try:
            stats_query = """
                SELECT 
                    COUNT(DISTINCT dz.id) as total_zones,
                    COUNT(df.id) as total_free_dates,
                    COUNT(CASE WHEN df.free_date >= CURRENT_DATE THEN 1 END) as upcoming_free_dates,
                    MIN(df.free_date) FILTER (WHERE df.free_date >= CURRENT_DATE) as next_free_date,
                    MAX(df.free_date) as last_scheduled_date
                FROM delivery_zones dz
                LEFT JOIN delivery_zone_free_dates df ON dz.id = df.zone_id
            """
            
            result = DatabaseService.execute_query(stats_query, fetch_one=True)
            
            if result:
                return {
                    'total_zones': result['total_zones'] or 0,
                    'total_free_dates': result['total_free_dates'] or 0,
                    'upcoming_free_dates': result['upcoming_free_dates'] or 0,
                    'next_free_date': result['next_free_date'],
                    'last_scheduled_date': result['last_scheduled_date']
                }
            else:
                return {
                    'total_zones': 0,
                    'total_free_dates': 0,
                    'upcoming_free_dates': 0,
                    'next_free_date': None,
                    'last_scheduled_date': None
                }
                
        except Exception as e:
            logger.error(f"Error getting zone statistics: {str(e)}")
            return {
                'total_zones': 0,
                'total_free_dates': 0,
                'upcoming_free_dates': 0,
                'next_free_date': None,
                'last_scheduled_date': None
            }


def run_daily_cleanup():
    """
    Main function to be called by the scheduler
    Returns result for logging/monitoring
    """
    logger.info("Starting daily delivery zone cleanup task")
    
    try:
        # Run the cleanup
        result = DeliveryZoneScheduler.cleanup_expired_free_dates()
        
        # Log the result
        if result['status'] == 'success':
            logger.info(f"Daily cleanup completed: {result['message']}")
        else:
            logger.error(f"Daily cleanup failed: {result['message']}")
            
        return result
        
    except Exception as e:
        error_msg = f"Critical error in daily cleanup task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'deleted_count': 0,
            'status': 'critical_error', 
            'message': error_msg
        }