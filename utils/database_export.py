
"""
Database export utility for Monthly Organics
Exports all database data to JSON format
"""
import json
import logging
from datetime import datetime, date
from decimal import Decimal
from services.database import DatabaseService

logger = logging.getLogger(__name__)

class DatabaseExporter:
    """Handles exporting database data to JSON format"""
    
    @staticmethod
    def serialize_value(value):
        """Convert database values to JSON-serializable format"""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif value is None:
            return None
        else:
            return value
    
    @staticmethod
    def get_table_data(table_name):
        """Get all data from a specific table"""
        try:
            query = f"SELECT * FROM {table_name} ORDER BY id"
            result = DatabaseService.execute_query(query)
            
            if not result:
                return []
            
            # Convert to list of dictionaries with serialized values
            table_data = []
            for row in result:
                row_dict = {}
                for key, value in dict(row).items():
                    row_dict[key] = DatabaseExporter.serialize_value(value)
                table_data.append(row_dict)
            
            return table_data
            
        except Exception as e:
            logger.error(f"Error exporting table {table_name}: {e}")
            return []
    
    @staticmethod
    def get_all_table_names():
        """Get list of all user tables in the database"""
        try:
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            result = DatabaseService.execute_query(query)
            
            if not result:
                return []
            
            return [row['table_name'] for row in result]
            
        except Exception as e:
            logger.error(f"Error getting table names: {e}")
            return []
    
    @staticmethod
    def export_full_database():
        """Export entire database to JSON format"""
        try:
            export_data = {
                'export_metadata': {
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'database_name': 'monthly_organics',
                    'export_type': 'full_database'
                },
                'tables': {}
            }
            
            # Get all table names
            table_names = DatabaseExporter.get_all_table_names()
            
            if not table_names:
                logger.warning("No tables found in database")
                return None
            
            # Export data from each table
            total_records = 0
            for table_name in table_names:
                logger.info(f"Exporting table: {table_name}")
                table_data = DatabaseExporter.get_table_data(table_name)
                export_data['tables'][table_name] = {
                    'record_count': len(table_data),
                    'data': table_data
                }
                total_records += len(table_data)
            
            # Add summary to metadata
            export_data['export_metadata']['total_tables'] = len(table_names)
            export_data['export_metadata']['total_records'] = total_records
            export_data['export_metadata']['tables_exported'] = table_names
            
            logger.info(f"Database export completed: {len(table_names)} tables, {total_records} records")
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting database: {e}")
            return None
    
    @staticmethod
    def export_specific_tables(table_list):
        """Export specific tables to JSON format"""
        try:
            export_data = {
                'export_metadata': {
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'database_name': 'monthly_organics',
                    'export_type': 'selective_tables',
                    'requested_tables': table_list
                },
                'tables': {}
            }
            
            total_records = 0
            exported_tables = []
            
            for table_name in table_list:
                logger.info(f"Exporting table: {table_name}")
                table_data = DatabaseExporter.get_table_data(table_name)
                
                if table_data is not None:  # Even empty tables should be included
                    export_data['tables'][table_name] = {
                        'record_count': len(table_data),
                        'data': table_data
                    }
                    total_records += len(table_data)
                    exported_tables.append(table_name)
            
            # Add summary to metadata
            export_data['export_metadata']['total_tables'] = len(exported_tables)
            export_data['export_metadata']['total_records'] = total_records
            export_data['export_metadata']['tables_exported'] = exported_tables
            
            logger.info(f"Selective export completed: {len(exported_tables)} tables, {total_records} records")
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting specific tables: {e}")
            return None
