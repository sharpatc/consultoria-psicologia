import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from .connection import get_db_connection

def init_db(db_path=None):
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

    # Seed default admin user if none exists
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute(
            'INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?, ?, ?, ?, ?)',
            ('admin', hashed_pw, 'admin', 'Administrador', 'admin@consultorio.com')
        )
        print("[Database] Usuario admin por defecto creado: admin / admin123")

    conn.commit()
    conn.close()
