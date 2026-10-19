import json

from ..database.connection import get_db


class ClinicalRepository:
    """Persistence for restricted clinical evaluations and session notes."""

    @staticmethod
    def list_evaluations():
        rows = get_db().execute('''
            SELECT e.id, e.patient_name, e.created_at, e.updated_at,
                   COUNT(s.id) AS session_count,
                   MAX(s.session_date) AS last_session
            FROM clinical_evaluations e
            LEFT JOIN clinical_sessions s ON s.evaluation_id = e.id
            GROUP BY e.id
            ORDER BY e.updated_at DESC, e.id DESC
        ''').fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_evaluation(evaluation_id):
        row = get_db().execute(
            'SELECT * FROM clinical_evaluations WHERE id = ?',
            (evaluation_id,)
        ).fetchone()
        if not row:
            return None
        evaluation = dict(row)
        evaluation['data'] = json.loads(evaluation.pop('data_json'))
        evaluation['sessions'] = ClinicalRepository.get_sessions(evaluation_id)
        return evaluation

    @staticmethod
    def create_evaluation(patient_name, data):
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO clinical_evaluations (patient_name, data_json) VALUES (?, ?)',
            (patient_name, json.dumps(data, ensure_ascii=False))
        )
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def update_evaluation(evaluation_id, patient_name, data):
        conn = get_db()
        cursor = conn.execute('''
            UPDATE clinical_evaluations
            SET patient_name = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (patient_name, json.dumps(data, ensure_ascii=False), evaluation_id))
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete_evaluation(evaluation_id):
        conn = get_db()
        cursor = conn.execute(
            'DELETE FROM clinical_evaluations WHERE id = ?', (evaluation_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def get_sessions(evaluation_id):
        rows = get_db().execute('''
            SELECT * FROM clinical_sessions
            WHERE evaluation_id = ?
            ORDER BY session_date DESC, id DESC
        ''', (evaluation_id,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create_session(evaluation_id, data):
        conn = get_db()
        cursor = conn.execute('''
            INSERT INTO clinical_sessions (
                evaluation_id, session_date, duration_minutes, modality,
                attendance, focus, interventions, progress, agreements,
                next_session
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            evaluation_id, data['session_date'], data['duration_minutes'],
            data['modality'], data['attendance'], data['focus'],
            data['interventions'], data['progress'], data['agreements'],
            data['next_session']
        ))
        conn.execute('''
            UPDATE clinical_evaluations SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (evaluation_id,))
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def update_session(session_id, data):
        conn = get_db()
        cursor = conn.execute('''
            UPDATE clinical_sessions SET
                session_date = ?, duration_minutes = ?, modality = ?,
                attendance = ?, focus = ?, interventions = ?, progress = ?,
                agreements = ?, next_session = ?
            WHERE id = ?
        ''', (
            data['session_date'], data['duration_minutes'], data['modality'],
            data['attendance'], data['focus'], data['interventions'],
            data['progress'], data['agreements'], data['next_session'],
            session_id
        ))
        if cursor.rowcount:
            conn.execute('''
                UPDATE clinical_evaluations SET updated_at = CURRENT_TIMESTAMP
                WHERE id = (SELECT evaluation_id FROM clinical_sessions WHERE id = ?)
            ''', (session_id,))
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete_session(session_id):
        conn = get_db()
        cursor = conn.execute(
            'DELETE FROM clinical_sessions WHERE id = ?', (session_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
