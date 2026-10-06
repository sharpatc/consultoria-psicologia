from flask import Blueprint, request, jsonify, session
from ..services.auth_service import AuthService
from ..models.user_repository import UserRepository

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    user, error = AuthService.authenticate(username, password)
    if error:
        status_code = 400 if 'requeridos' in error else 401
        return jsonify({'error': error}), status_code

    AuthService.establish_session(user)

    return jsonify({
        'success': True,
        'message': 'Login exitoso',
        'username': user['username'],
        'role': user.get('role', 'viewer')
    }), 200

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    AuthService.clear_session()
    return jsonify({'success': True, 'message': 'Logout exitoso'}), 200

@auth_bp.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        user = UserRepository.get_by_id(session['user_id'])
        if user:
            return jsonify({
                'authenticated': True,
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name'],
                'email': user['email']
            }), 200
    return jsonify({'authenticated': False}), 200
