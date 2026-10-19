from datetime import date

from flask import Blueprint, jsonify, request

from ..middlewares.auth_middleware import admin_required
from ..models.clinical_repository import ClinicalRepository

clinical_bp = Blueprint('clinical', __name__)

EVALUATION_FIELDS = {
    'nombre': 150,
    'fecha_nacimiento': 20,
    'edad': 20,
    'sexo': 40,
    'escuela': 200,
    'grado': 100,
    'direccion': 500,
    'padre': 150,
    'madre': 150,
    'tutor': 150,
    'telefonos': 100,
    'motivo_consulta': 4000,
    'historia_problema': 4000,
    'antecedentes_prenatales': 4000,
    'antecedentes_parto': 4000,
    'sostuvo_cabeza': 100,
    'se_sento': 100,
    'gateo': 100,
    'camino': 100,
    'primeras_palabras': 100,
    'control_esfinteres': 100,
    'antecedentes_medicos': 4000,
    'antecedentes_familiares': 4000,
    'dinamica_familiar': 4000,
    'area_escolar': 4000,
    'area_emocional': 1000,
    'area_conductual': 4000,
    'sueno': 500,
    'alimentacion': 500,
    'pantallas': 500,
    'juego': 500,
    'observacion_clinica': 4000,
    'fortalezas': 4000,
    'impresion_clinica': 4000,
    'objetivos_terapeuticos': 4000,
    'plan_intervencion': 4000,
    'consentimiento_tutor': 150,
    'firma_psicologa': 150,
}

SESSION_FIELDS = {
    'session_date': 20,
    'modality': 20,
    'attendance': 20,
    'focus': 2000,
    'interventions': 4000,
    'progress': 4000,
    'agreements': 2000,
    'next_session': 500,
}


def validate_text_fields(data, fields):
    if not isinstance(data, dict):
        return None, 'El formulario debe contener un objeto de datos'
    unknown = set(data) - set(fields)
    if unknown:
        return None, 'El formulario contiene campos no permitidos'
    cleaned = {}
    for name, value in data.items():
        if not isinstance(value, str):
            return None, f'El campo {name} debe ser texto'
        value = value.strip()
        if len(value) > fields[name]:
            return None, f'El campo {name} supera el maximo de {fields[name]} caracteres'
        cleaned[name] = value
    return cleaned, None


def validate_evaluation(data):
    cleaned, error = validate_text_fields(data, EVALUATION_FIELDS)
    if error:
        return None, error
    cleaned['nombre'] = cleaned.get('nombre', '').strip()
    cleaned['motivo_consulta'] = cleaned.get('motivo_consulta', '').strip()
    if not cleaned['nombre'] or not cleaned['motivo_consulta']:
        return None, 'El nombre y el motivo de consulta son obligatorios'
    birth_date = cleaned.get('fecha_nacimiento', '')
    if birth_date:
        try:
            date.fromisoformat(birth_date)
        except ValueError:
            return None, 'La fecha de nacimiento debe tener formato AAAA-MM-DD'
    return cleaned, None


def validate_session(data):
    allowed = set(SESSION_FIELDS) | {'duration_minutes'}
    cleaned, error = validate_text_fields(
        {key: value for key, value in data.items() if key != 'duration_minutes'}
        if isinstance(data, dict) else data,
        SESSION_FIELDS
    )
    if error:
        return None, error
    if not isinstance(data, dict) or set(data) - allowed:
        return None, 'El formulario contiene campos no permitidos'
    duration = data.get('duration_minutes')
    if isinstance(duration, bool) or not isinstance(duration, int):
        return None, 'La duracion debe ser un numero de minutos'
    if duration < 15 or duration > 240:
        return None, 'La duracion debe estar entre 15 y 240 minutos'
    try:
        date.fromisoformat(cleaned.get('session_date', ''))
    except ValueError:
        return None, 'La fecha de atencion debe tener formato AAAA-MM-DD'
    if cleaned.get('modality') not in {'Presencial', 'Virtual'}:
        return None, 'Selecciona una modalidad valida'
    if cleaned.get('attendance') not in {'Atendida', 'No asistio', 'Cancelada'}:
        return None, 'Selecciona un estado de asistencia valido'
    if not cleaned.get('focus'):
        return None, 'El tema de la atencion es obligatorio'
    cleaned['duration_minutes'] = duration
    return cleaned, None


@clinical_bp.route('/api/clinical/evaluations', methods=['GET'])
@admin_required
def list_evaluations():
    return jsonify(ClinicalRepository.list_evaluations())


@clinical_bp.route('/api/clinical/evaluations', methods=['POST'])
@admin_required
def create_evaluation():
    data, error = validate_evaluation(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    evaluation_id = ClinicalRepository.create_evaluation(data['nombre'], data)
    return jsonify({'success': True, 'id': evaluation_id}), 201


@clinical_bp.route('/api/clinical/evaluations/<int:evaluation_id>', methods=['GET'])
@admin_required
def get_evaluation(evaluation_id):
    evaluation = ClinicalRepository.get_evaluation(evaluation_id)
    if not evaluation:
        return jsonify({'error': 'Evaluacion no encontrada'}), 404
    return jsonify(evaluation)


@clinical_bp.route('/api/clinical/evaluations/<int:evaluation_id>', methods=['PUT'])
@admin_required
def update_evaluation(evaluation_id):
    data, error = validate_evaluation(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    if not ClinicalRepository.update_evaluation(
        evaluation_id, data['nombre'], data
    ):
        return jsonify({'error': 'Evaluacion no encontrada'}), 404
    return jsonify({'success': True})


@clinical_bp.route('/api/clinical/evaluations/<int:evaluation_id>', methods=['DELETE'])
@admin_required
def delete_evaluation(evaluation_id):
    if not ClinicalRepository.delete_evaluation(evaluation_id):
        return jsonify({'error': 'Evaluacion no encontrada'}), 404
    return jsonify({'success': True})


@clinical_bp.route(
    '/api/clinical/evaluations/<int:evaluation_id>/sessions', methods=['POST']
)
@admin_required
def create_session(evaluation_id):
    if not ClinicalRepository.get_evaluation(evaluation_id):
        return jsonify({'error': 'Evaluacion no encontrada'}), 404
    data, error = validate_session(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    session_id = ClinicalRepository.create_session(evaluation_id, data)
    return jsonify({'success': True, 'id': session_id}), 201


@clinical_bp.route('/api/clinical/sessions/<int:session_id>', methods=['PUT'])
@admin_required
def update_session(session_id):
    data, error = validate_session(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    if not ClinicalRepository.update_session(session_id, data):
        return jsonify({'error': 'Atencion no encontrada'}), 404
    return jsonify({'success': True})


@clinical_bp.route('/api/clinical/sessions/<int:session_id>', methods=['DELETE'])
@admin_required
def delete_session(session_id):
    if not ClinicalRepository.delete_session(session_id):
        return jsonify({'error': 'Atencion no encontrada'}), 404
    return jsonify({'success': True})
