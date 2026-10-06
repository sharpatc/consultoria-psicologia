from ..database.connection import get_db

class UserRepository:
    """Repository handling all database queries and transactions for Users."""

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        return conn.execute(
            'SELECT id, username, role, full_name, email, password_hash FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        return conn.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()

    @staticmethod
    def get_by_email(email, exclude_id=None):
        conn = get_db()
        if exclude_id is not None:
            return conn.execute(
                'SELECT id FROM users WHERE email = ? AND id != ?',
                (email, exclude_id)
            ).fetchone()
        return conn.execute(
            'SELECT id FROM users WHERE email = ?',
            (email,)
        ).fetchone()

    @staticmethod
    def get_all():
        conn = get_db()
        users = conn.execute(
            'SELECT id, username, role, full_name, email FROM users ORDER BY id ASC'
        ).fetchall()
        return [dict(u) for u in users]

    @staticmethod
    def create(username, password_hash, role='viewer', full_name=''):
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)',
            (username, password_hash, role, full_name or '')
        )
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def update_profile(user_id, full_name, email):
        conn = get_db()
        conn.execute(
            'UPDATE users SET full_name = ?, email = ? WHERE id = ?',
            (full_name, email, user_id)
        )
        conn.commit()

    @staticmethod
    def update_password(user_id, new_password_hash):
        conn = get_db()
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (new_password_hash, user_id)
        )
        conn.commit()

    @staticmethod
    def delete(user_id):
        conn = get_db()
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()

    @staticmethod
    def count_admins():
        conn = get_db()
        row = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'").fetchone()
        return row['count'] if row else 0
