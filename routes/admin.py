
"""
Admin routes for Monthly Organics
Handles admin dashboard, export, and management functionality
"""
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from utils.database_export import DatabaseExporter
from admin_auth import admin_required
import json
import io
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/export', methods=['GET', 'POST'])
@admin_required
def export_database():
    """Handle database export with decryption options"""
    if request.method == 'GET':
        # Get list of tables for selective export
        tables = DatabaseExporter.get_all_table_names()
        return render_template('admin/admin_export.html', tables=tables)
    
    try:
        # Get form data
        export_type = request.form.get('export_type', 'full')
        export_format = request.form.get('export_format', 'json')
        decrypt_data = request.form.get('decrypt_data', 'false') == 'true'
        
        logger.info(f"Export request: type={export_type}, format={export_format}, decrypt={decrypt_data}")
        
        # Export data based on type
        if export_type == 'full':
            export_data = DatabaseExporter.export_full_database(decrypt_data=decrypt_data)
        else:  # selective
            selected_tables = request.form.getlist('tables')
            if not selected_tables:
                flash('Please select at least one table for export.', 'error')
                tables = DatabaseExporter.get_all_table_names()
                return render_template('admin/admin_export.html', tables=tables)
            export_data = DatabaseExporter.export_specific_tables(selected_tables, decrypt_data=decrypt_data)
        
        if not export_data:
            flash('Export failed. Please try again.', 'error')
            tables = DatabaseExporter.get_all_table_names()
            return render_template('admin/admin_export.html', tables=tables)
        
        # Generate filename with timestamp and decryption status
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        decrypt_suffix = '_decrypted' if decrypt_data else '_encrypted'
        
        # Create file based on format
        if export_format == 'json':
            filename = f'monthly_organics_export{decrypt_suffix}_{timestamp}.json'
            file_data = json.dumps(export_data, indent=2).encode('utf-8')
            mimetype = 'application/json'
            
        elif export_format == 'csv':
            filename = f'monthly_organics_export{decrypt_suffix}_{timestamp}.zip'
            file_data = DatabaseExporter.export_to_csv(export_data, export_type)
            mimetype = 'application/zip'
            
        elif export_format == 'xlsx':
            filename = f'monthly_organics_export{decrypt_suffix}_{timestamp}.xlsx'
            file_data = DatabaseExporter.export_to_xlsx(export_data, export_type)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        if not file_data:
            flash('Failed to generate export file. Please try again.', 'error')
            tables = DatabaseExporter.get_all_table_names()
            return render_template('admin/admin_export.html', tables=tables)
        
        # Create file object for download
        file_obj = io.BytesIO(file_data)
        file_obj.seek(0)
        
        logger.info(f"Export completed: {filename}")
        
        return send_file(
            file_obj,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        flash('Export failed due to an error. Please try again.', 'error')
        tables = DatabaseExporter.get_all_table_names()
        return render_template('admin/admin_export.html', tables=tables)
