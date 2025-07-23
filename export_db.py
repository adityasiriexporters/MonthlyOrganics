
#!/usr/bin/env python3
"""
Quick database export script for Monthly Organics
"""

import sys
import os

# Add the services directory to the path
sys.path.append('services')

# Import and run the exporter
from database_exporter import DatabaseExporter

def quick_export():
    try:
        exporter = DatabaseExporter()
        success = exporter.export_database('monthly_organics_backup.json')
        
        if success:
            print("✅ Database exported successfully to 'monthly_organics_backup.json'")
        else:
            print("❌ Export failed")
            
    except Exception as e:
        print(f"❌ Export error: {e}")

if __name__ == "__main__":
    quick_export()
