from functools import wraps
from flask import session, jsonify
from ..models.user_repository import UserRepository

def login_required(f):
    """Restricts route access to authenticated users with active session."""
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    """Restricts route access exclusively to users with 'admin' role."""
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user = UserRepository.get_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return wrap
