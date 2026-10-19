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
    notas_privadas TEXT DEFAULT '',
    recordatorio_enviado_at TEXT,
    recordatorio_intentos INTEGER NOT NULL DEFAULT 0,
    recordatorio_ultimo_intento_at TEXT
);

CREATE TABLE IF NOT EXISTS clinical_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clinical_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL,
    session_date TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    modality TEXT NOT NULL,
    attendance TEXT NOT NULL,
    focus TEXT NOT NULL,
    interventions TEXT DEFAULT '',
    progress TEXT DEFAULT '',
    agreements TEXT DEFAULT '',
    next_session TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES clinical_evaluations(id) ON DELETE CASCADE
);

-- Indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_clinical_sessions_evaluation_date
    ON clinical_sessions(evaluation_id, session_date DESC);
