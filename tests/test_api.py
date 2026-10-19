import unittest
import json
import sqlite3
import smtplib
from pathlib import Path
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import create_app
from backend.config import ProductionConfig, TestingConfig
from backend.models.user_repository import UserRepository
from backend.models.message_repository import MessageRepository
from backend.services.appointment_reminder_service import process_due_reminders
from backend.services.email_service import EmailService
from backend.utils.validators import is_valid_email, sanitize_input

class PsychologyAppTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client with in-memory database."""
        self.app = create_app(config_class=TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()
        database_anchor = self.app.extensions.pop('database_anchor', None)
        if database_anchor:
            database_anchor.close()

    def login_admin(self):
        return self.client.post('/api/login', json={
            'username': 'admin',
            'password': 'admin123'
        })

    # --- VALIDATOR TESTS ---
    def test_validators(self):
        self.assertTrue(is_valid_email('test@example.com'))
        self.assertFalse(is_valid_email('invalid-email'))
        self.assertEqual(sanitize_input('  <script>alert(1)</script>  '), '&lt;script&gt;alert(1)&lt;/script&gt;')

    # --- STATIC ROUTE TESTS ---
    def test_static_routes(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

        logo = self.client.get('/img/logo.jpg')
        self.assertEqual(logo.status_code, 200)
        self.assertEqual(logo.mimetype, 'image/jpeg')

        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)

    def test_database_persists_between_app_instances(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = type(
                'PersistentConfig',
                (TestingConfig,),
                {'DB_PATH': str(Path(temp_dir) / 'persistent.sqlite')}
            )
            first_client = create_app(config_class=config).test_client()
            response = first_client.post('/api/contact', json={
                'nombre': 'Paciente persistente',
                'email': 'persistente@example.com',
                'mensaje': 'Verificacion de persistencia'
            })
            self.assertEqual(response.status_code, 200)

            second_client = create_app(config_class=config).test_client()
            login = second_client.post('/api/login', json={
                'username': 'admin',
                'password': 'admin123'
            })
            self.assertEqual(login.status_code, 200)
            messages = second_client.get('/api/messages').get_json()
            self.assertTrue(any(
                message['nombre'] == 'Paciente persistente'
                for message in messages
            ))

    def test_legacy_database_migrates_appointment_columns_before_indexes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / 'legacy.sqlite'
            connection = sqlite3.connect(database_path)
            connection.executescript('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    email TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO messages (nombre, email, mensaje)
                VALUES ('Paciente anterior', 'legacy@example.com', 'Cita existente');
            ''')
            connection.commit()
            connection.close()

            config = type(
                'LegacyDatabaseConfig',
                (TestingConfig,),
                {'DB_PATH': str(database_path)}
            )
            app = create_app(config_class=config)

            with app.app_context():
                message = MessageRepository.get_by_id(1)
                self.assertEqual(message['nombre'], 'Paciente anterior')
                self.assertEqual(message['estado'], 'Pendiente')
                self.assertIsNone(message['recordatorio_enviado_at'])

    def test_production_rejects_weak_secrets(self):
        weak_secret_config = type(
            'WeakSecretConfig',
            (ProductionConfig,),
            {
                'SECRET_KEY': 'psicologo_secret_key_12345',
                'ADMIN_USERNAME': 'admin',
                'ADMIN_PASSWORD': 'admin123'
            }
        )
        with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
            create_app(config_class=weak_secret_config)

        weak_password_config = type(
            'WeakPasswordConfig',
            (ProductionConfig,),
            {
                'SECRET_KEY': 'a-long-random-looking-secret-key-for-test-only',
                'ADMIN_USERNAME': 'admin',
                'ADMIN_PASSWORD': 'short'
            }
        )
        with self.assertRaisesRegex(RuntimeError, 'ADMIN_PASSWORD'):
            create_app(config_class=weak_password_config)

    # --- CONTACT API TESTS ---
    def test_contact_submission_success(self):
        payload = {
            'nombre': 'Juan Perez',
            'email': 'juan@example.com',
            'mensaje': 'Deseo agendar una consulta psicologica presencial.'
        }
        res = self.client.post('/api/contact', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

    def test_contact_submission_invalid_email(self):
        payload = {
            'nombre': 'Juan Perez',
            'email': 'email_no_valido',
            'mensaje': 'Consulta'
        }
        res = self.client.post('/api/contact', json=payload)
        self.assertEqual(res.status_code, 400)

    def test_contact_submission_missing_fields(self):
        payload = {'nombre': 'Juan Perez'}
        res = self.client.post('/api/contact', json=payload)
        self.assertEqual(res.status_code, 400)

    # --- AUTH API TESTS ---
    def test_login_success(self):
        res = self.login_admin()
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('username'), 'admin')

    def test_login_invalid_credentials(self):
        res = self.client.post('/api/login', json={
            'username': 'admin',
            'password': 'wrongpassword'
        })
        self.assertEqual(res.status_code, 401)

    def test_check_auth_flow(self):
        # Before login
        res = self.client.get('/api/check-auth')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json().get('authenticated'))

        # After login
        self.login_admin()
        res = self.client.get('/api/check-auth')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get('authenticated'))

        # After logout
        res_logout = self.client.post('/api/logout')
        self.assertEqual(res_logout.status_code, 200)
        res_check = self.client.get('/api/check-auth')
        self.assertFalse(res_check.get_json().get('authenticated'))

    # --- DASHBOARD & APPOINTMENTS TESTS ---
    def test_unauthorized_dashboard_stats(self):
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 401)

    def test_authorized_dashboard_and_appointments(self):
        self.login_admin()

        # Create contact message
        self.client.post('/api/contact', json={
            'nombre': 'Maria Lopez',
            'email': 'maria@example.com',
            'mensaje': 'Necesito cita urgente.'
        })

        # Check stats
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()
        self.assertGreaterEqual(stats['total_messages'], 1)

        # Get messages
        res_msgs = self.client.get('/api/messages')
        self.assertEqual(res_msgs.status_code, 200)
        messages = res_msgs.get_json()
        self.assertTrue(len(messages) > 0)
        msg_id = messages[0]['id']

        # Schedule appointment
        res_sch = self.client.post(f'/api/messages/{msg_id}/schedule', json={
            'fecha_cita': '2026-10-15 10:00',
            'modalidad': 'Virtual',
            'notas': 'Primera sesion'
        })
        self.assertEqual(res_sch.status_code, 200)
        self.assertTrue(res_sch.get_json()['email_simulated'])
        self.assertEqual(
            MessageRepository.get_by_id(msg_id)['fecha_cita'],
            '2026-10-15 10:00:00'
        )

        # Cancel appointment
        res_cancel = self.client.post(f'/api/messages/{msg_id}/cancel')
        self.assertEqual(res_cancel.status_code, 200)

    def test_schedule_reports_saved_appointment_when_email_fails(self):
        self.login_admin()
        self.client.post('/api/contact', json={
            'nombre': 'Paciente correo',
            'email': 'correo@example.com',
            'mensaje': 'Solicitud de cita'
        })
        msg_id = MessageRepository.get_all()[0]['id']

        with patch.object(
            EmailService,
            'send_appointment_confirmation',
            side_effect=smtplib.SMTPException('SMTP no disponible')
        ):
            response = self.client.post(f'/api/messages/{msg_id}/schedule', json={
                'fecha_cita': '2026-10-15T10:00:00',
                'modalidad': 'Virtual'
            })

        self.assertEqual(response.status_code, 502)
        self.assertTrue(response.get_json()['appointment_scheduled'])
        self.assertEqual(MessageRepository.get_by_id(msg_id)['estado'], 'Agendada')

    def test_schedule_rejects_non_iso_appointment_dates(self):
        self.login_admin()
        self.client.post('/api/contact', json={
            'nombre': 'Paciente fecha',
            'email': 'fecha@example.com',
            'mensaje': 'Solicitud de cita'
        })
        msg_id = MessageRepository.get_all()[0]['id']

        response = self.client.post(f'/api/messages/{msg_id}/schedule', json={
            'fecha_cita': '2026-10-15 a las 10:00',
            'modalidad': 'Virtual'
        })

        self.assertEqual(response.status_code, 400)

    def test_confirmation_uses_smtp_and_sends_to_patient(self):
        self.app.config.update({
            'EMAIL_USER': 'clinic@example.com',
            'EMAIL_PASS': 'smtp-password'
        })
        smtp_context = MagicMock()
        smtp_server = smtp_context.__enter__.return_value

        with patch('backend.services.email_service.smtplib.SMTP', return_value=smtp_context) as smtp:
            result = EmailService.send_appointment_confirmation(
                patient_name='Paciente',
                patient_email='patient@example.com',
                appointment_date='2026-10-15 10:00:00',
                modality='Virtual'
            )

        self.assertEqual(result, {'sent': True, 'simulated': False})
        smtp.assert_called_once_with('smtp.gmail.com', 587, timeout=20)
        smtp_server.login.assert_called_once_with(
            'clinic@example.com',
            'smtp-password'
        )
        sent_message = smtp_server.send_message.call_args.args[0]
        self.assertEqual(sent_message['To'], 'patient@example.com')

    def test_reminder_is_sent_once_on_appointment_day(self):
        self.app.config.update({
            'EMAIL_USER': 'clinic@example.com',
            'EMAIL_PASS': 'smtp-password'
        })
        message_id = MessageRepository.create(
            'Paciente recordatorio',
            'recordatorio@example.com',
            'Solicitud de cita'
        )
        MessageRepository.schedule(
            message_id,
            '2026-10-15 10:00:00',
            'Virtual',
            ''
        )
        now = datetime(2026, 10, 15, 8, 0, tzinfo=ZoneInfo('America/Panama'))

        with patch(
            'backend.services.appointment_reminder_service.EmailService.send_appointment_reminder',
            return_value={'sent': True, 'simulated': False}
        ) as send_reminder:
            sent = process_due_reminders(now)
            repeated_sent = process_due_reminders(now)

        self.assertEqual(sent, 1)
        self.assertEqual(repeated_sent, 0)
        send_reminder.assert_called_once()
        self.assertIsNotNone(
            MessageRepository.get_by_id(message_id)['recordatorio_enviado_at']
        )

    def test_reminder_does_not_send_before_appointment_day(self):
        self.app.config.update({
            'EMAIL_USER': 'clinic@example.com',
            'EMAIL_PASS': 'smtp-password'
        })
        message_id = MessageRepository.create(
            'Paciente futura',
            'futura@example.com',
            'Solicitud de cita'
        )
        MessageRepository.schedule(
            message_id,
            '2026-10-16 10:00:00',
            'Presencial',
            ''
        )

        with patch(
            'backend.services.appointment_reminder_service.EmailService.send_appointment_reminder'
        ) as send_reminder:
            sent = process_due_reminders(
                datetime(2026, 10, 15, 8, 0, tzinfo=ZoneInfo('America/Panama'))
            )

        self.assertEqual(sent, 0)
        send_reminder.assert_not_called()

    def test_clinical_evaluation_and_session_crud(self):
        self.assertEqual(self.client.get('/api/clinical/evaluations').status_code, 401)
        self.login_admin()

        evaluation_data = {
            'nombre': 'Paciente de prueba',
            'edad': '12',
            'fecha_nacimiento': '2014-01-12',
            'motivo_consulta': 'Evaluacion de prueba automatizada'
        }
        created = self.client.post('/api/clinical/evaluations', json=evaluation_data)
        self.assertEqual(created.status_code, 201)
        evaluation_id = created.get_json()['id']

        detail = self.client.get(f'/api/clinical/evaluations/{evaluation_id}')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()['data']['nombre'], 'Paciente de prueba')
        self.assertEqual(detail.get_json()['sessions'], [])

        session_data = {
            'session_date': '2026-10-15',
            'duration_minutes': 50,
            'modality': 'Presencial',
            'attendance': 'Atendida',
            'focus': 'Seguimiento de prueba',
            'interventions': 'Entrevista',
            'progress': 'Sin hallazgos de prueba',
            'agreements': 'Continuar seguimiento',
            'next_session': '2026-10-22'
        }
        created_session = self.client.post(
            f'/api/clinical/evaluations/{evaluation_id}/sessions',
            json=session_data
        )
        self.assertEqual(created_session.status_code, 201)
        session_id = created_session.get_json()['id']
        invalid_session = {**session_data, 'duration_minutes': 12}
        self.assertEqual(
            self.client.post(
                f'/api/clinical/evaluations/{evaluation_id}/sessions',
                json=invalid_session
            ).status_code,
            400
        )

        evaluation = self.client.get(f'/api/clinical/evaluations/{evaluation_id}').get_json()
        self.assertEqual(len(evaluation['sessions']), 1)
        self.assertEqual(evaluation['sessions'][0]['focus'], 'Seguimiento de prueba')

        updated_session = {**session_data, 'focus': 'Seguimiento actualizado'}
        self.assertEqual(
            self.client.put(f'/api/clinical/sessions/{session_id}', json=updated_session).status_code,
            200
        )
        self.assertEqual(self.client.delete(f'/api/clinical/sessions/{session_id}').status_code, 200)
        self.assertEqual(self.client.delete(f'/api/clinical/evaluations/{evaluation_id}').status_code, 200)
        self.assertEqual(self.client.get(f'/api/clinical/evaluations/{evaluation_id}').status_code, 404)

    def test_clinical_records_require_administrator(self):
        self.login_admin()
        created = self.client.post('/api/clinical/evaluations', json={
            'nombre': 'Paciente de prueba',
            'motivo_consulta': 'Solo para validar permisos'
        })
        self.assertEqual(created.status_code, 201)
        evaluation_id = created.get_json()['id']

        viewer = self.client.post('/api/users', json={
            'username': 'viewer_clinico',
            'password': 'password1234',
            'role': 'viewer',
            'full_name': 'Visualizador de prueba'
        })
        self.assertEqual(viewer.status_code, 201)
        self.client.post('/api/logout')
        self.client.post('/api/login', json={
            'username': 'viewer_clinico',
            'password': 'password1234'
        })

        self.assertEqual(self.client.get('/api/clinical/evaluations').status_code, 403)
        self.assertEqual(
            self.client.get(f'/api/clinical/evaluations/{evaluation_id}').status_code,
            403
        )

    def test_viewer_can_only_manage_pending_appointments(self):
        self.login_admin()
        pending = self.client.post('/api/contact', json={
            'nombre': 'Cita pendiente',
            'email': 'pendiente@example.com',
            'mensaje': 'Solicita una cita'
        })
        scheduled = self.client.post('/api/contact', json={
            'nombre': 'Cita agendada',
            'email': 'agendada@example.com',
            'mensaje': 'Ya fue agendada'
        })
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(scheduled.status_code, 200)
        messages = self.client.get('/api/messages').get_json()
        scheduled_id = next(
            message['id'] for message in messages
            if message['email'] == 'agendada@example.com'
        )
        pending_id = next(
            message['id'] for message in messages
            if message['email'] == 'pendiente@example.com'
        )
        self.assertEqual(self.client.post(
            f'/api/messages/{scheduled_id}/schedule',
            json={
                'fecha_cita': '2026-10-15 10:00',
                'modalidad': 'Virtual',
                'notas': 'Nota privada de administrador'
            }
        ).status_code, 200)

        viewer = self.client.post('/api/users', json={
            'username': 'viewer_citas',
            'password': 'password1234',
            'role': 'viewer',
            'full_name': 'Visualizador de citas'
        })
        self.assertEqual(viewer.status_code, 201)
        self.client.post('/api/logout')
        self.assertEqual(self.client.post('/api/login', json={
            'username': 'viewer_citas',
            'password': 'password1234'
        }).status_code, 200)

        self.assertEqual(self.client.get('/api/dashboard/stats').status_code, 200)
        viewer_messages = self.client.get('/api/messages')
        self.assertEqual(viewer_messages.status_code, 200)
        self.assertTrue(all(
            not message['notas_privadas']
            for message in viewer_messages.get_json()
        ))
        self.assertEqual(self.client.get('/api/users').status_code, 403)
        self.assertEqual(self.client.put('/api/profile', json={
            'full_name': 'No permitido',
            'email': 'viewer@example.com'
        }).status_code, 403)
        self.assertEqual(self.client.put('/api/profile/password', json={
            'current_password': 'password1234',
            'new_password': 'another-password'
        }).status_code, 403)
        self.assertEqual(self.client.post(
            f'/api/messages/{scheduled_id}/schedule',
            json={'fecha_cita': '2026-10-16 10:00', 'modalidad': 'Virtual'}
        ).status_code, 403)
        self.assertEqual(
            self.client.post(f'/api/messages/{scheduled_id}/cancel').status_code,
            403
        )
        self.assertEqual(self.client.post(
            f'/api/messages/{pending_id}/schedule',
            json={
                'fecha_cita': '2026-10-16 10:00',
                'modalidad': 'Presencial',
                'notas': 'Este texto no debe almacenarse'
            }
        ).status_code, 200)

        self.client.post('/api/logout')
        self.assertEqual(self.login_admin().status_code, 200)
        final_messages = self.client.get('/api/messages').get_json()
        accepted = next(
            message for message in final_messages
            if message['id'] == pending_id
        )
        self.assertEqual(accepted['estado'], 'Agendada')
        self.assertEqual(accepted['notas_privadas'], '')

    # --- USER MANAGEMENT TESTS ---
    def test_user_crud(self):
        self.login_admin()

        # Create new user
        res_create = self.client.post('/api/users', json={
            'username': 'asistente1',
            'password': 'password1234',
            'role': 'viewer',
            'full_name': 'Asistente Consultorio'
        })
        self.assertEqual(res_create.status_code, 201)
        new_id = res_create.get_json().get('id')

        # List users
        res_list = self.client.get('/api/users')
        self.assertEqual(res_list.status_code, 200)
        users = res_list.get_json()
        self.assertTrue(any(u['username'] == 'asistente1' for u in users))

        # Delete user
        res_del = self.client.delete(f'/api/users/{new_id}')
        self.assertEqual(res_del.status_code, 200)

if __name__ == '__main__':
    unittest.main()
