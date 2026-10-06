from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from ..models.user_repository import UserRepository

class AuthService:
    """Service handling password encryption, credential verification, and sessions."""

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    @staticmethod
    def verify_password(stored_hash, password):
        if not stored_hash or not password:
            return False
        return check_password_hash(stored_hash, password)

    @classmethod
    def authenticate(cls, username, password):
        """
        Authenticates a user by username and password.
        Returns (user_dict, error_string).
        """
        if not username or not password:
            return None, 'Usuario y contrasena son requeridos'

        user = UserRepository.get_by_username(username.strip())
        if not user or not cls.verify_password(user['password_hash'], password):
            return None, 'Credenciales invalidas'

        return dict(user), None

    @staticmethod
    def establish_session(user):
        """Sets session variables for authenticated user."""
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user.get('role', 'viewer')

    @staticmethod
    def clear_session():
        """Clears all session variables."""
        session.clear()
