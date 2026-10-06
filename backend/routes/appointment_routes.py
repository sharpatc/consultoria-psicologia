from flask import Blueprint, request, jsonify
from ..utils.validators import sanitize_input, is_valid_email
from ..middlewares.auth_middleware import login_required
from ..models.message_repository import MessageRepository
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

    msg = MessageRepository.get_by_id(msg_id)
    if not msg:
        return jsonify({'error': 'Mensaje no encontrado'}), 404

    try:
        MessageRepository.schedule(msg_id, fecha_cita, modalidad, notas or '')
        EmailService.send_appointment_confirmation(
            patient_name=msg['nombre'],
            patient_email=msg['email'],
            appointment_date=fecha_cita,
            modality=modalidad
        )
    except Exception as e:
        print(f"[Error schedule_appointment]: {e}")
        return jsonify({'error': f'Error al procesar: {str(e)}'}), 500

    return jsonify({'success': True, 'message': 'Cita agendada exitosamente'}), 200

@appointment_bp.route('/api/messages/<int:msg_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(msg_id):
    msg = MessageRepository.get_by_id(msg_id)
    if not msg:
        return jsonify({'error': 'Mensaje no encontrado'}), 404

    try:
        MessageRepository.cancel(msg_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'success': True, 'message': 'Cita cancelada'}), 200
