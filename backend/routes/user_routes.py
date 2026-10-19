import sqlite3
from flask import Blueprint, request, jsonify, session
from ..utils.validators import sanitize_input, is_valid_email
from ..middlewares.auth_middleware import login_required, admin_required
from ..models.user_repository import UserRepository
from ..services.auth_service import AuthService

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/profile', methods=['PUT'])
@admin_required
def update_profile():
    data = request.get_json(silent=True) or {}
    full_name = sanitize_input(data.get('full_name', ''), 100)
    email = sanitize_input(data.get('email', ''), 150)

    if not full_name or not email:
        return jsonify({'error': 'Nombre y correo son requeridos'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Correo electronico invalido'}), 400

    try:
        existing = UserRepository.get_by_email(email, exclude_id=session['user_id'])
        if existing:
            return jsonify({'error': 'Este correo ya esta en uso'}), 400

        UserRepository.update_profile(session['user_id'], full_name, email)
        return jsonify({'success': True, 'message': 'Perfil actualizado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/api/profile/password', methods=['PUT'])
@admin_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Contrasena actual y nueva contrasena son requeridas'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'La nueva contrasena debe tener al menos 8 caracteres'}), 400

    user = UserRepository.get_by_id(session['user_id'])
    if not user or not AuthService.verify_password(user['password_hash'], current_password):
        return jsonify({'error': 'La contrasena actual es incorrecta'}), 400

    try:
        new_hash = AuthService.hash_password(new_password)
        UserRepository.update_password(session['user_id'], new_hash)
        return jsonify({'success': True, 'message': 'Contrasena actualizada correctamente'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    users = UserRepository.get_all()
    return jsonify(users), 200

@user_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = sanitize_input(data.get('username'), 50)
    password = data.get('password', '')
    role = sanitize_input(data.get('role', 'viewer'), 20)
    full_name = sanitize_input(data.get('full_name', ''), 100)

    if not username or not password:
        return jsonify({'error': 'Usuario y contrasena son requeridos'}), 400

    if len(password) < 8:
        return jsonify({'error': 'La contrasena debe tener al menos 8 caracteres'}), 400

    if role not in ['admin', 'viewer']:
        return jsonify({'error': 'Rol invalido'}), 400

    hashed_pw = AuthService.hash_password(password)

    try:
        last_id = UserRepository.create(username, hashed_pw, role, full_name or '')
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El usuario ya existe'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'success': True, 'message': 'Usuario creado', 'id': last_id}), 201

@user_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400

    target = UserRepository.get_by_id(user_id)
    if not target:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if target['role'] == 'admin':
        admin_count = UserRepository.count_admins()
        if admin_count <= 1:
            return jsonify({'error': 'No se puede eliminar el ultimo administrador'}), 400

    try:
        UserRepository.delete(user_id)
    except Exception:
        return jsonify({'error': 'Error al eliminar usuario'}), 500

    return jsonify({'success': True, 'message': 'Usuario eliminado'}), 200
