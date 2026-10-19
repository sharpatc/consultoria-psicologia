import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from .connection import get_db_connection

def init_db(db_path=None, admin_username='admin', admin_password='admin123'):
    """
    Initializes the database schema, runs migrations for legacy databases,
    and seeds default administrator account if not present.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    schema_file = Path(__file__).resolve().parent / 'schema.sql'
    if schema_file.exists():
        with open(schema_file, 'r', encoding='utf-8') as f:
            cursor.executescript(f.read())
    else:
        # Fallback inline schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                full_name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                estado TEXT DEFAULT 'Pendiente',
                fecha_cita TEXT,
                modalidad TEXT,
                notas_privadas TEXT DEFAULT ''
            )
        ''')

    # Migration safety for legacy SQLite databases with missing columns
    columns_to_add = [
        ('messages', 'estado', 'TEXT DEFAULT "Pendiente"'),
        ('messages', 'fecha_cita', 'TEXT'),
        ('messages', 'modalidad', 'TEXT'),
        ('messages', 'notas_privadas', 'TEXT DEFAULT ""'),
        ('messages', 'recordatorio_enviado_at', 'TEXT'),
        ('messages', 'recordatorio_intentos', 'INTEGER NOT NULL DEFAULT 0'),
        ('messages', 'recordatorio_ultimo_intento_at', 'TEXT'),
        ('users', 'role', 'TEXT DEFAULT "admin"'),
        ('users', 'full_name', 'TEXT DEFAULT ""'),
        ('users', 'email', 'TEXT DEFAULT ""'),
        ('users', 'created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
    ]

    for table, col, col_def in columns_to_add:
        try:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}')
        except sqlite3.OperationalError:
            pass  # Column already exists

    cursor.executescript('''
        CREATE INDEX IF NOT EXISTS idx_messages_estado ON messages(estado);
        CREATE INDEX IF NOT EXISTS idx_messages_fecha ON messages(fecha DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_email ON messages(email);
        CREATE INDEX IF NOT EXISTS idx_messages_recordatorios
            ON messages(estado, recordatorio_enviado_at);
    ''')

    # Keep concurrent requests and background database readers reliable.
    if not (db_path or '').startswith('file:') or 'mode=memory' not in (db_path or ''):
        cursor.execute('PRAGMA journal_mode = WAL')

    # Seed the configured administrator without replacing existing credentials.
    cursor.execute('SELECT id FROM users WHERE username = ?', (admin_username,))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash(admin_password)
        cursor.execute(
            'INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?, ?, ?, ?, ?)',
            (admin_username, hashed_pw, 'admin', 'Administrador', 'admin@consultorio.com')
        )
        print(f"[Database] Usuario administrador inicial creado: {admin_username}")

    conn.commit()
    conn.close()
