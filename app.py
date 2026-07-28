from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import html
import re

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'psicologo_secret_key_12345')
DB_PATH = 'database.sqlite'

def sanitize(value):
    if value is None:
        return None
    return html.escape(str(value))

def sanitize_input(value, max_length=500):
    if value is None:
        return None
    cleaned = html.escape(str(value).strip())
    return cleaned[:max_length] if cleaned else None

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            full_name TEXT DEFAULT '',
            email TEXT DEFAULT ''
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

    try:
        c.execute('ALTER TABLE messages ADD COLUMN estado TEXT DEFAULT "Pendiente"')
        c.execute('ALTER TABLE messages ADD COLUMN fecha_cita TEXT')
        c.execute('ALTER TABLE messages ADD COLUMN modalidad TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE messages ADD COLUMN notas_privadas TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    # Ensure role column exists for users
    try:
        c.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "admin"')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE users ADD COLUMN email TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        hashed_pw = generate_password_hash('admin123')
        c.execute('INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?, ?, ?, ?, ?)',
                  ('admin', hashed_pw, 'admin', 'Administrador', 'admin@consultorio.com'))
        print("Usuario admin por defecto creado: admin / admin123")

    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        conn = get_db_connection()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return wrap

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/admin')
def serve_admin():
    return send_from_directory('.', 'admin/index.html')

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.json
    nombre = sanitize_input(data.get('nombre'), 100)
    email = sanitize_input(data.get('email'), 150)
    mensaje = sanitize_input(data.get('mensaje'), 2000)

    if not nombre or not email or not mensaje:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Correo electronico invalido'}), 400

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO messages (nombre, email, mensaje) VALUES (?, ?, ?)',
                     (nombre, email, mensaje))
        conn.commit()
    except Exception:
        return jsonify({'error': 'Error al guardar el mensaje'}), 500
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Mensaje enviado correctamente'}), 200

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Usuario y contrasena son requeridos'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({
            'success': True,
            'message': 'Login exitoso',
            'username': user['username'],
            'role': user['role']
        })

    return jsonify({'error': 'Credenciales invalidas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout exitoso'})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT id, username, role, full_name, email FROM users WHERE id = ?',
                           (session['user_id'],)).fetchone()
        conn.close()
        if user:
            return jsonify({
                'authenticated': True,
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name'],
                'email': user['email']
            })
    return jsonify({'authenticated': False})

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    conn = get_db_connection()
    total_messages = conn.execute('SELECT COUNT(*) as count FROM messages').fetchone()['count']
    pending = conn.execute("SELECT COUNT(*) as count FROM messages WHERE estado = 'Pendiente'").fetchone()['count']
    scheduled = conn.execute("SELECT COUNT(*) as count FROM messages WHERE estado = 'Agendada'").fetchone()['count']
    cancelled = conn.execute("SELECT COUNT(*) as count FROM messages WHERE estado = 'Cancelada'").fetchone()['count']
    total_patients = conn.execute('SELECT COUNT(DISTINCT email) as count FROM messages').fetchone()['count']
    upcoming = conn.execute("""
        SELECT COUNT(*) as count FROM messages
        WHERE estado = 'Agendada' AND fecha_cita IS NOT NULL
        AND fecha_cita >= datetime('now', 'localtime')
    """).fetchone()['count']
    conn.close()
    return jsonify({
        'total_messages': total_messages,
        'pending': pending,
        'scheduled': scheduled,
        'cancelled': cancelled,
        'total_patients': total_patients,
        'upcoming': upcoming
    })

@app.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    conn = get_db_connection()
    messages = conn.execute('SELECT * FROM messages ORDER BY fecha DESC').fetchall()
    conn.close()
    return jsonify([{
        'id': m['id'],
        'nombre': m['nombre'],
        'email': m['email'],
        'mensaje': m['mensaje'],
        'fecha': m['fecha'],
        'estado': m['estado'],
        'fecha_cita': m['fecha_cita'],
        'modalidad': m['modalidad'],
        'notas_privadas': m['notas_privadas'] or ''
    } for m in messages])

@app.route('/api/messages/<int:msg_id>/schedule', methods=['POST'])
@login_required
def schedule_appointment(msg_id):
    data = request.json
    fecha_cita = sanitize_input(data.get('fecha_cita'), 100)
    modalidad = sanitize_input(data.get('modalidad'), 20)
    notas = sanitize_input(data.get('notas', ''), 1000)

    if not fecha_cita or not modalidad:
        return jsonify({'error': 'Fecha y modalidad son requeridas'}), 400

    if modalidad not in ['Virtual', 'Presencial']:
        return jsonify({'error': 'Modalidad invalida'}), 400

    conn = get_db_connection()
    try:
        msg = conn.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()
        if not msg:
            return jsonify({'error': 'Mensaje no encontrado'}), 404

        conn.execute('''
            UPDATE messages
            SET estado = 'Agendada', fecha_cita = ?, modalidad = ?, notas_privadas = ?
            WHERE id = ?
        ''', (fecha_cita, modalidad, notas or '', msg_id))
        conn.commit()

        sender_email = os.environ.get('EMAIL_USER', '')
        sender_password = os.environ.get('EMAIL_PASS', '')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <meta charset="UTF-8">
          <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f7f5f0; margin: 0; padding: 20px; color: #333; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2ded4; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            .email-header {{ background: linear-gradient(135deg, #1e3a5f, #2563eb); color: #ffffff; padding: 30px 20px; text-align: center; }}
            .email-header h1 {{ margin: 0; font-size: 24px; letter-spacing: 1px; }}
            .email-header p {{ margin: 5px 0 0 0; font-size: 14px; color: #93c5fd; letter-spacing: 2px; }}
            .email-body {{ padding: 30px 25px; line-height: 1.6; }}
            .appointment-card {{ background-color: #f0f7ff; border-left: 4px solid #2563eb; border-radius: 8px; padding: 20px; margin: 25px 0; border: 1px solid #dbeafe; }}
            .appointment-item {{ display: flex; align-items: center; margin-bottom: 10px; font-size: 15px; color: #1e3a5f; }}
            .appointment-item strong {{ width: 140px; color: #333; }}
            .email-footer {{ background-color: #f8fafc; padding: 20px; text-align: center; font-size: 13px; color: #666; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="email-container">
            <div class="email-header">
              <h1>ZUMAIKIRA BAILEY</h1>
              <p>PSICOLOGA - C.I.P. 8362</p>
            </div>
            <div class="email-body">
              <h2 style="color: #1e3a5f; margin-top: 0;">Hola, {sanitize(msg['nombre'])}!</h2>
              <p>Nos complace confirmarte que tu cita ha sido agendada con exito.</p>
              <div class="appointment-card">
                <div class="appointment-item"><strong>Fecha y Hora:</strong> {sanitize(fecha_cita)}</div>
                <div class="appointment-item"><strong>Modalidad:</strong> {sanitize(modalidad)}</div>
                <div class="appointment-item"><strong>Ubicacion:</strong> Atlantic Plaza, 1er piso, local 127, oficina #224</div>
              </div>
              <p style="font-style: italic; color: #2563eb;">"Tu bienestar mental es tu mejor version y estoy aqui para ayudarte en tu proceso."</p>
              <p>Si necesitas reprogramar o tienes alguna duda previa a la consulta, puedes comunicarte al <strong>+507 6235-281</strong>.</p>
            </div>
            <div class="email-footer">
              <p style="margin: 0; font-weight: bold; color: #1e3a5f;">Escucha - Comprende - Acompana</p>
              <p style="margin: 5px 0 0 0; font-size: 12px; color: #888;">Atencion a Ninos, Adolescentes y Adultos</p>
            </div>
          </div>
        </body>
        </html>
        """

        if not sender_email or not sender_password:
            print("\n" + "="*50)
            print("SIMULACION DE ENVIO DE CORREO")
            print(f"Para: {msg['email']}")
            print(f"Asunto: Confirmacion de Cita - Zumaikira Bailey Psicologa")
            print(f"Fecha: {fecha_cita}")
            print("="*50 + "\n")
        else:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            email_msg = MIMEMultipart("alternative")
            email_msg["Subject"] = "Confirmacion de Cita Psicologica - Zumaikira Bailey"
            email_msg["From"] = f"Zumaikira Bailey Psicologa <{sender_email}>"
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

@app.route('/api/messages/<int:msg_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(msg_id):
    conn = get_db_connection()
    try:
        msg = conn.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()
        if not msg:
            return jsonify({'error': 'Mensaje no encontrado'}), 404

        conn.execute("UPDATE messages SET estado = 'Cancelada' WHERE id = ?", (msg_id,))
        conn.commit()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
    return jsonify({'success': True, 'message': 'Cita cancelada'})

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.json
    full_name = sanitize_input(data.get('full_name', ''), 100)
    email = sanitize_input(data.get('email', ''), 150)

    if not full_name or not email:
        return jsonify({'error': 'Nombre y correo son requeridos'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Correo electronico invalido'}), 400

    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT id FROM users WHERE email = ? AND id != ?',
                               (email, session['user_id'])).fetchone()
        if existing:
            return jsonify({'error': 'Este correo ya esta en uso'}), 400

        conn.execute('UPDATE users SET full_name = ?, email = ? WHERE id = ?',
                     (full_name, email, session['user_id']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Perfil actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/profile/password', methods=['PUT'])
@login_required
def change_password():
    data = request.json
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Contrasena actual y nueva contrasena son requeridas'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'La nueva contrasena debe tener al menos 8 caracteres'}), 400

    conn = get_db_connection()
    try:
        user = conn.execute('SELECT password_hash FROM users WHERE id = ?',
                           (session['user_id'],)).fetchone()
        if not user or not check_password_hash(user['password_hash'], current_password):
            return jsonify({'error': 'La contrasena actual es incorrecta'}), 400

        new_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, session['user_id']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Contrasena actualizada correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role, full_name, email FROM users').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.json
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

    hashed_pw = generate_password_hash(password)

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)',
            (username, hashed_pw, role, full_name or ''))
        conn.commit()
        last_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El usuario ya existe'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Usuario creado', 'id': last_id}), 201

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400

    conn = get_db_connection()
    try:
        target = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
        if not target:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        if target['role'] == 'admin':
            admin_count = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'").fetchone()['count']
            if admin_count <= 1:
                return jsonify({'error': 'No se puede eliminar el ultimo administrador'}), 400

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
