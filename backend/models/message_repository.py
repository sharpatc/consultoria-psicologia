from ..database.connection import get_db

class MessageRepository:
    """Repository handling all database queries and transactions for Messages / Appointments."""

    @staticmethod
    def create(nombre, email, mensaje):
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO messages (nombre, email, mensaje) VALUES (?, ?, ?)',
            (nombre, email, mensaje)
        )
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def get_all():
        conn = get_db()
        messages = conn.execute('SELECT * FROM messages ORDER BY fecha DESC').fetchall()
        return [{
            'id': m['id'],
            'nombre': m['nombre'],
            'email': m['email'],
            'mensaje': m['mensaje'],
            'fecha': m['fecha'],
            'estado': m['estado'],
            'fecha_cita': m['fecha_cita'],
            'modalidad': m['modalidad'],
            'notas_privadas': m['notas_privadas'] or ''
        } for m in messages]

    @staticmethod
    def get_by_id(msg_id):
        conn = get_db()
        return conn.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()

    @staticmethod
    def schedule(msg_id, fecha_cita, modalidad, notas_privadas):
        conn = get_db()
        conn.execute('''
            UPDATE messages
            SET estado = 'Agendada', fecha_cita = ?, modalidad = ?, notas_privadas = ?
            WHERE id = ?
        ''', (fecha_cita, modalidad, notas_privadas or '', msg_id))
        conn.commit()

    @staticmethod
    def cancel(msg_id):
        conn = get_db()
        conn.execute("UPDATE messages SET estado = 'Cancelada' WHERE id = ?", (msg_id,))
        conn.commit()

    @staticmethod
    def get_dashboard_stats():
        conn = get_db()
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

        return {
            'total_messages': total_messages,
            'pending': pending,
            'scheduled': scheduled,
            'cancelled': cancelled,
            'total_patients': total_patients,
            'upcoming': upcoming
        }
