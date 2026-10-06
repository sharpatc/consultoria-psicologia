from .auth_routes import auth_bp
from .appointment_routes import appointment_bp
from .dashboard_routes import dashboard_bp
from .user_routes import user_bp
from .static_routes import static_bp

def register_routes(app):
    """Registers all blueprints to the Flask application instance."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(user_bp)
    # Register static_bp last to avoid capturing API routes
    app.register_blueprint(static_bp)

__all__ = ['register_routes', 'auth_bp', 'appointment_bp', 'dashboard_bp', 'user_bp', 'static_bp']
