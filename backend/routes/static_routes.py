import os
from flask import Blueprint, send_from_directory, current_app, abort

static_bp = Blueprint('static_pages', __name__)

@static_bp.route('/')
def serve_index():
    return send_from_directory(current_app.static_folder, 'index.html')

@static_bp.route('/admin')
@static_bp.route('/admin/')
def serve_admin():
    return send_from_directory(current_app.static_folder, 'admin/index.html')

@static_bp.route('/<path:path>')
def serve_static(path):
    # Do not intercept API routes
    if path.startswith('api/'):
        abort(404)
        
    file_path = os.path.join(current_app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(current_app.static_folder, path)
    abort(404)
