from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import html

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'psicologo_secret_key_12345')
DB_PATH = 'database.sqlite'

def sanitize(value):
    if value is None:
        return None
    return html.escape(str(value))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Añadir nuevas columnas si no existen (SQLite ALTER TABLE)
    try:
        c.execute('ALTER TABLE messages ADD COLUMN estado TEXT DEFAULT "Pendiente"')
        c.execute('ALTER TABLE messages ADD COLUMN fecha_cita TEXT')
        c.execute('ALTER TABLE messages ADD COLUMN modalidad TEXT')
    except sqlite3.OperationalError:
        pass # Las columnas ya existen
    
    # Create default admin if not exists
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        hashed_pw = generate_password_hash('admin123')
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('admin', hashed_pw))
        print("Usuario admin por defecto creado: admin / admin123")
        
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# --- Rutas del Frontend ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/admin')
def serve_admin():
    return send_from_directory('.', 'admin/index.html')

# --- Rutas de la API ---

# 1. Contact Form (Public)
@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.json
    nombre = sanitize(data.get('nombre'))
    email = sanitize(data.get('email'))
    mensaje = sanitize(data.get('mensaje'))
    
    if not nombre or not email or not mensaje:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400
        
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO messages (nombre, email, mensaje) VALUES (?, ?, ?)',
                     (nombre, email, mensaje))
        conn.commit()
    except Exception as e:
        return jsonify({'error': 'Error al guardar el mensaje'}), 500
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'Mensaje enviado correctamente'}), 200

# 2. Login & Session
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'success': True, 'message': 'Login exitoso'})
    
    return jsonify({'error': 'Credenciales inválidas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'success': True, 'message': 'Logout exitoso'})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'username': session['username']})
    return jsonify({'authenticated': False})

# 3. Get messages (Protected)
@app.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    conn = get_db_connection()
    messages = conn.execute('SELECT * FROM messages ORDER BY fecha DESC').fetchall()
    conn.close()
    return jsonify([{
        'id': m['id'],
        'nombre': sanitize(m['nombre']),
        'email': sanitize(m['email']),
        'mensaje': sanitize(m['mensaje']),
        'fecha': m['fecha'],
        'estado': m['estado'],
        'fecha_cita': m['fecha_cita'],
        'modalidad': m['modalidad']
    } for m in messages])

# 3.5 Schedule Appointment (Protected)
@app.route('/api/messages/<int:msg_id>/schedule', methods=['POST'])
@login_required
def schedule_appointment(msg_id):
    data = request.json
    fecha_cita = sanitize(data.get('fecha_cita'))
    modalidad = sanitize(data.get('modalidad'))

    if not fecha_cita or not modalidad:
        return jsonify({'error': 'Fecha y modalidad son requeridas'}), 400

    if modalidad not in ['Virtual', 'Presencial']:
        return jsonify({'error': 'Modalidad inválida'}), 400

    conn = get_db_connection()
    try:
        msg = conn.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()
        if not msg:
            return jsonify({'error': 'Mensaje no encontrado'}), 404

        conn.execute('''
            UPDATE messages 
            SET estado = 'Agendada', fecha_cita = ?, modalidad = ?
            WHERE id = ?
        ''', (fecha_cita, modalidad, msg_id))
        conn.commit()
        
        sender_email = os.environ.get('EMAIL_USER', '')
        sender_password = os.environ.get('EMAIL_PASS', '')
        
        # Plantilla de Correo Profesional con la Identidad Visual de Zumaikira Bailey
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <meta charset="UTF-8">
          <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f7f5f0; margin: 0; padding: 20px; color: #333; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2ded4; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            .email-header {{ background: linear-gradient(135deg, #3B7A75, #2D5E5A); color: #ffffff; padding: 30px 20px; text-align: center; }}
            .email-header h1 {{ margin: 0; font-size: 24px; font-family: Georgia, serif; letter-spacing: 1px; }}
            .email-header p {{ margin: 5px 0 0 0; font-size: 14px; color: #d4af37; letter-spacing: 2px; }}
            .email-body {{ padding: 30px 25px; line-height: 1.6; }}
            .appointment-card {{ background-color: #faf8f5; border-left: 4px solid #C5A059; border-radius: 8px; padding: 20px; margin: 25px 0; border: 1px solid #efeae0; }}
            .appointment-item {{ display: flex; align-items: center; margin-bottom: 10px; font-size: 15px; color: #2D5E5A; }}
            .appointment-item strong {{ width: 140px; color: #333; }}
            .email-footer {{ background-color: #FAF8F5; padding: 20px; text-align: center; font-size: 13px; color: #666; border-top: 1px solid #efeae0; }}
            .btn-location {{ display: inline-block; background-color: #3B7A75; color: #ffffff !important; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; }}
          </style>
        </head>
        <body>
          <div class="email-container">
            <div class="email-header">
              <h1>ZUMAIKIRA BAILEY</h1>
              <p>PSICÓLOGA • C.I.P. 8362</p>
            </div>
            <div class="email-body">
              <h2 style="color: #3B7A75; margin-top: 0;">¡Hola, {sanitize(msg['nombre'])}!</h2>
              <p>Nos complace confirmarte que tu cita ha sido agendada con éxito.</p>
              
              <div class="appointment-card">
                <div class="appointment-item">
                  <strong>📅 Fecha y Hora:</strong> {fecha_cita}
                </div>
                <div class="appointment-item">
                  <strong>📍 Modalidad:</strong> {modalidad}
                </div>
                <div class="appointment-item">
                  <strong>🏥 Ubicación:</strong> Atlantic Plaza, 1er piso, local 127, oficina #224
                </div>
              </div>

              <p style="font-style: italic; color: #C5A059;">"Tu bienestar mental es tu mejor versión y estoy aquí para ayudarte en tu proceso."</p>

              <p>Si necesitas reprogramar o tienes alguna duda previa a la consulta, puedes comunicarte al <strong>+507 6235-281</strong>.</p>
            </div>
            <div class="email-footer">
              <p style="margin: 0; font-weight: bold; color: #3B7A75;">Escucha • Comprende • Acompaña</p>
              <p style="margin: 5px 0 0 0; font-size: 12px; color: #888;">Atención a Niños, Adolescentes y Adultos</p>
            </div>
          </div>
        </body>
        </html>
        """
        
        if not sender_email or not sender_password:
            # Modo Simulación (Para probar localmente sin requerir claves activas)
            print("\n" + "="*50)
            print("SIMULACIÓN DE ENVÍO DE CORREO (Configura EMAIL_USER y EMAIL_PASS para envío real)")
            print(f"Para: {msg['email']}")
            print(f"Asunto: Confirmación de Cita - Zumaikira Bailey Psicóloga")
            print(f"Mensaje generado exitosamente para fecha: {fecha_cita}")
            print("="*50 + "\n")
        else:
            # Envío Real Activo mediante SMTP de Gmail
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            email_msg = MIMEMultipart("alternative")
            email_msg["Subject"] = "Confirmación de Cita Psicológica - Zumaikira Bailey"
            email_msg["From"] = f"Zumaikira Bailey Psicóloga <{sender_email}>"
            email_msg["Reply-To"] = "Zumaikirabailey98@gmail.com"
            email_msg["To"] = msg['email']
            email_msg.attach(MIMEText(html_content, "html"))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(email_msg)
            server.quit()
            print(f"Correo real enviado a {msg['email']}")
            
    except Exception as e:
        print(f"Error al agendar o enviar correo: {e}")
        return jsonify({'error': f'Error al procesar: {str(e)}'}), 500
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Cita agendada exitosamente'})

# 4. Get users (Protected)
@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username FROM users').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

# 5. Create user (Protected)
@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña son requeridos'}), 400
        
    hashed_pw = generate_password_hash(password)
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                              (username, hashed_pw))
        conn.commit()
        last_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El usuario ya existe'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'Usuario creado', 'id': last_id}), 201

# 6. Delete user (Protected)
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400
        
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
    except Exception as e:
        return jsonify({'error': 'Error al eliminar usuario'}), 500
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'Usuario eliminado'})

if __name__ == '__main__':
    print("Iniciando servidor en http://localhost:3000")
    app.run(debug=True, port=3000)
