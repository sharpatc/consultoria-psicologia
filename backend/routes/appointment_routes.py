import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, request, jsonify, session, current_app
from ..utils.validators import sanitize_input, is_valid_email
from ..middlewares.auth_middleware import login_required, admin_required
from ..models.message_repository import MessageRepository
from ..models.user_repository import UserRepository
from ..services.email_service import EmailService

appointment_bp = Blueprint('appointment', __name__)

@appointment_bp.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json(silent=True) or {}
    nombre = sanitize_input(data.get('nombre'), 100)
    email = sanitize_input(data.get('email'), 150)
    mensaje = sanitize_input(data.get('mensaje'), 2000)

    if not nombre or not email or not mensaje:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Correo electronico invalido'}), 400

    try:
        MessageRepository.create(nombre, email, mensaje)
    except Exception as e:
        return jsonify({'error': 'Error al guardar el mensaje'}), 500

    return jsonify({'success': True, 'message': 'Mensaje enviado correctamente'}), 200

@appointment_bp.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    messages = MessageRepository.get_all()
    user = UserRepository.get_by_id(session['user_id'])
    if user and user['role'] == 'viewer':
        for message in messages:
            message['notas_privadas'] = ''
    return jsonify(messages), 200

@appointment_bp.route('/api/messages/<int:msg_id>/schedule', methods=['POST'])
@login_required
def schedule_appointment(msg_id):
    data = request.get_json(silent=True) or {}
    fecha_cita = sanitize_input(data.get('fecha_cita'), 100)
    modalidad = sanitize_input(data.get('modalidad'), 20)
    notas = sanitize_input(data.get('notas', ''), 1000)

    if not fecha_cita or not modalidad:
        return jsonify({'error': 'Fecha y modalidad son requeridas'}), 400

    if modalidad not in ['Virtual', 'Presencial']:
        return jsonify({'error': 'Modalidad invalida'}), 400

    try:
        appointment_datetime = datetime.fromisoformat(fecha_cita)
        clinic_timezone = ZoneInfo(current_app.config['TIMEZONE'])
    except (TypeError, ValueError):
        return jsonify({'error': 'La fecha y hora debe tener formato AAAA-MM-DD HH:MM'}), 400

    if appointment_datetime.tzinfo:
        appointment_datetime = appointment_datetime.astimezone(clinic_timezone)
    fecha_cita = appointment_datetime.strftime('%Y-%m-%d %H:%M:%S')

    msg = MessageRepository.get_by_id(msg_id)
    if not msg:
        return jsonify({'error': 'Mensaje no encontrado'}), 404

    user = UserRepository.get_by_id(session['user_id'])
    is_viewer = user and user['role'] == 'viewer'
    if is_viewer and msg['estado'] != 'Pendiente':
        return jsonify({'error': 'Solo puedes aceptar citas pendientes'}), 403

    try:
        MessageRepository.schedule(
            msg_id,
            fecha_cita,
            modalidad,
            '' if is_viewer else notas or ''
        )
        email_result = EmailService.send_appointment_confirmation(
            patient_name=msg['nombre'],
            patient_email=msg['email'],
            appointment_date=fecha_cita,
            modality=modalidad
        )
    except (smtplib.SMTPException, OSError, TimeoutError):
        current_app.logger.exception(
            'La cita %s se guardo, pero fallo el envio del correo de confirmacion.',
            msg_id
        )
        return jsonify({
            'success': False,
            'appointment_scheduled': True,
            'error': 'La cita quedó agendada, pero no se pudo enviar el correo. Contacta al administrador.'
        }), 502

    if email_result['simulated']:
        return jsonify({
            'success': True,
            'email_sent': False,
            'email_simulated': True,
            'message': 'La cita quedó agendada, pero falta configurar el correo SMTP.'
        }), 200

    return jsonify({
        'success': True,
        'email_sent': True,
        'email_simulated': False,
        'message': 'Cita agendada y correo de confirmación enviado.'
    }), 200

@appointment_bp.route('/api/messages/<int:msg_id>/cancel', methods=['POST'])
@admin_required
def cancel_appointment(msg_id):
    msg = MessageRepository.get_by_id(msg_id)
    if not msg:
        return jsonify({'error': 'Mensaje no encontrado'}), 404

    try:
        MessageRepository.cancel(msg_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'success': True, 'message': 'Cita cancelada'}), 200
