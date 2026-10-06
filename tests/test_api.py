import unittest
import json
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import create_app
from backend.config import TestingConfig
from backend.models.user_repository import UserRepository
from backend.models.message_repository import MessageRepository
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

        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)

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

        # Cancel appointment
        res_cancel = self.client.post(f'/api/messages/{msg_id}/cancel')
        self.assertEqual(res_cancel.status_code, 200)

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
