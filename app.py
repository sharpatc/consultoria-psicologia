"""
Punto de entrada principal de la aplicacion (WSGI Entry Point).
Compatible con Gunicorn (Procfile: web: gunicorn app:app) y ejecucion local directa.
"""
import os
from backend import create_app
from backend.database import get_db_connection, init_db

# Instancia de la aplicacion Flask creada via Application Factory
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1')
    print("=" * 60)
    print(f"  Servidor Consultorio Psicologico iniciado")
    print(f"  URL Local: http://localhost:{port}")
    print(f"  Panel Admin: http://localhost:{port}/admin")
    print(f"  Entorno: {'Desarrollo (Debug)' if debug else 'Produccion'}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug)
