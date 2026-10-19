from pathlib import Path
import sqlite3
from uuid import uuid4
from flask import Flask, jsonify, request
from flask_cors import CORS
from .config import get_config
from .database import close_db, init_db
from .routes import register_routes

def create_app(config_class=None):
    """
    Application Factory for Flask.
    Creates and configures the Flask application instance.
    """
    project_root = Path(__file__).resolve().parent.parent
    templates_dir = project_root / 'backend' / 'templates'

    app = Flask(
        __name__,
        static_folder=str(project_root),
        static_url_path='',
        template_folder=str(templates_dir)
    )

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    if app.config.get('IS_PRODUCTION'):
        secret_key = app.config.get('SECRET_KEY', '')
        if len(secret_key) < 32 or secret_key == 'psicologo_secret_key_12345':
            raise RuntimeError(
                'En produccion, SECRET_KEY debe tener al menos 32 caracteres aleatorios.'
            )
        if not app.config.get('ADMIN_USERNAME') or len(app.config.get('ADMIN_PASSWORD', '')) < 12:
            raise RuntimeError(
                'En produccion, define ADMIN_USERNAME y un ADMIN_PASSWORD de al menos 12 caracteres.'
            )

    if app.config.get('DB_PATH') == ':memory:':
        database_uri = f'file:consultoria_{uuid4().hex}?mode=memory&cache=shared'
        app.config['DB_PATH'] = database_uri
        app.extensions['database_anchor'] = sqlite3.connect(
            database_uri, uri=True, check_same_thread=False
        )

    # Enable CORS
    CORS(app)

    # Database teardown registration
    app.teardown_appcontext(close_db)

    # Initialize Database Schema & Seed default records
    with app.app_context():
        init_db(
            app.config.get('DB_PATH'),
            admin_username=app.config['ADMIN_USERNAME'],
            admin_password=app.config['ADMIN_PASSWORD']
        )

    # Register all Blueprints
    register_routes(app)

    # Custom JSON error handler for API routes
    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Recurso API no encontrado'}), 404
        return e

    @app.errorhandler(500)
    def handle_server_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Error interno del servidor'}), 500
        return e

    return app

__all__ = ['create_app']
