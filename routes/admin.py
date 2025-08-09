
"""
Admin routes for Monthly Organics
Handles admin dashboard, export, and management functionality
"""
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from utils.database_export import DatabaseExporter
from admin_auth import admin_required
from services.database import DatabaseService
from werkzeug.utils import secure_filename
import json
import io
import os
import uuid
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
            flash('Export failed during file generation. Please try again.', 'error')
            tables = DatabaseExporter.get_all_table_names()
            return render_template('admin/admin_export.html', tables=tables)
        
        # Create file stream for download
        file_stream = io.BytesIO(file_data)
        file_stream.seek(0)
        
        logger.info(f"Export successful: {filename} ({len(file_data)} bytes)")
        return send_file(
            file_stream,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
    except Exception as e:
        logger.error(f"Error during database export: {e}")
        flash(f'Export failed: {str(e)}', 'error')
        tables = DatabaseExporter.get_all_table_names()
        return render_template('admin/admin_export.html', tables=tables)

@admin_bp.route('/zoho-integration')
@admin_required
def zoho_integration():
    """Zoho Integration management page"""
    try:
        logger.info("Loading Zoho Integration admin page")
        return render_template('admin/zoho_integration.html')
    except Exception as e:
        logger.error(f"Error loading Zoho integration page: {e}")
        flash('Error loading Zoho integration page. Please try again.', 'error')
        return redirect(url_for('admin_dashboard'))

@admin_bp.route('/categories', methods=['GET'])
@admin_required
def categories():
    """Display categories management"""
    try:
        query = "SELECT id, name, icon_url FROM categories ORDER BY name"
        categories_data = DatabaseService.execute_query(query)
        
        # Ensure we have a proper list and clean the data
        categories_list = []
        if categories_data:
            for cat in categories_data:
                clean_category = {
                    'id': cat.get('id'),
                    'name': cat.get('name', '').strip() if cat.get('name') else 'Unnamed Category',
                    'icon_url': cat.get('icon_url', '').strip() if cat.get('icon_url') else None
                }
                categories_list.append(clean_category)
        
        # Log for debugging
        logger.info(f"Fetched {len(categories_list)} categories for admin")
        for cat in categories_list:
            logger.info(f"Category: ID={cat['id']}, Name='{cat['name']}', Icon='{cat['icon_url']}'")
        
        return jsonify({
            'success': True,
            'categories': categories_list
        })
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load categories',
            'message': str(e)
        }), 500

@admin_bp.route('/categories', methods=['POST'])
@admin_required
def add_category():
    """Add new category"""
    try:
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Category name is required'}), 400
            
        # Handle icon upload
        icon_url = None
        if 'icon' in request.files:
            file = request.files['icon']
            if file and file.filename:
                icon_url = save_category_icon(file)
                
        # Insert category
        query = "INSERT INTO categories (name, icon_url) VALUES (%s, %s) RETURNING id"
        result = DatabaseService.execute_query(query, (name, icon_url))
        
        if result:
            return jsonify({
                'success': True, 
                'category': {
                    'id': result[0]['id'], 
                    'name': name, 
                    'icon_url': icon_url
                }
            })
        else:
            return jsonify({'error': 'Failed to create category'}), 500
            
    except Exception as e:
        logger.error(f"Error adding category: {e}")
        return jsonify({'error': 'Failed to create category'}), 500

@admin_bp.route('/categories/<int:category_id>', methods=['PUT'])
@admin_required
def update_category(category_id):
    """Update category"""
    try:
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Category name is required'}), 400
            
        # Get current category
        current_query = "SELECT icon_url FROM categories WHERE id = %s"
        current = DatabaseService.execute_query(current_query, (category_id,))
        if not current:
            return jsonify({'error': 'Category not found'}), 404
            
        icon_url = current[0]['icon_url']
        
        # Handle icon upload
        if 'icon' in request.files:
            file = request.files['icon']
            if file and file.filename:
                # Delete old icon file if exists
                if icon_url and icon_url.startswith('/static/'):
                    old_file_path = icon_url[1:]  # Remove leading /
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        
                icon_url = save_category_icon(file)
                
        # Update category
        query = "UPDATE categories SET name = %s, icon_url = %s WHERE id = %s"
        DatabaseService.execute_query(query, (name, icon_url, category_id))
        
        return jsonify({
            'success': True,
            'category': {
                'id': category_id,
                'name': name,
                'icon_url': icon_url
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating category {category_id}: {e}")
        return jsonify({'error': 'Failed to update category'}), 500

@admin_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    """Delete category"""
    try:
        # Check if category has products
        check_query = "SELECT COUNT(*) as count FROM products WHERE category_id = %s"
        result = DatabaseService.execute_query(check_query, (category_id,))
        
        if result and result[0]['count'] > 0:
            return jsonify({'error': 'Cannot delete category with existing products'}), 400
            
        # Get category icon to delete file
        icon_query = "SELECT icon_url FROM categories WHERE id = %s"
        icon_result = DatabaseService.execute_query(icon_query, (category_id,))
        
        # Delete category
        delete_query = "DELETE FROM categories WHERE id = %s"
        DatabaseService.execute_query(delete_query, (category_id,))
        
        # Delete icon file if exists
        if icon_result and icon_result[0]['icon_url']:
            icon_url = icon_result[0]['icon_url']
            if icon_url.startswith('/static/'):
                file_path = icon_url[1:]  # Remove leading /
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {e}")
        return jsonify({'error': 'Failed to delete category'}), 500

def save_category_icon(file):
    """Save uploaded category icon and return URL"""
    if file and file.filename:
        filename = secure_filename(file.filename)
        name_part, ext = os.path.splitext(filename)
        unique_filename = f"category_{uuid.uuid4().hex[:8]}{ext}"
        
        upload_dir = 'static/uploads/categories'
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        return f"/static/uploads/categories/{unique_filename}"
    return None

@admin_bp.route('/zoho-connect')
@admin_required
def zoho_connect():
    """Route to initiate Zoho authorization from admin panel."""
    return redirect(url_for('zoho.authorize'))

@admin_bp.route('/zoho-status')
@admin_required  
def zoho_status():
    """Check Zoho connection status from admin panel."""
    return redirect(url_for('zoho.connection_status'))
