-- Schema for Psychology Practice Management System

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    full_name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

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
);

-- Indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_messages_estado ON messages(estado);
CREATE INDEX IF NOT EXISTS idx_messages_fecha ON messages(fecha DESC);
CREATE INDEX IF NOT EXISTS idx_messages_email ON messages(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
