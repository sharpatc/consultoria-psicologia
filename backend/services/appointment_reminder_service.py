import logging
import smtplib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

from ..models.message_repository import MessageRepository
from .email_service import EmailService

logger = logging.getLogger(__name__)


def _parse_appointment_datetime(value, timezone):
    try:
        appointment_datetime = datetime.fromisoformat(value)
    except ValueError:
        appointment_datetime = None
        for date_format in ('%Y-%m-%d a las %H:%M', '%d/%m/%Y a las %H:%M'):
            try:
                appointment_datetime = datetime.strptime(value, date_format)
                break
            except ValueError:
                continue
        if appointment_datetime is None:
            return None

    if appointment_datetime.tzinfo:
        return appointment_datetime.astimezone(timezone)
    return appointment_datetime.replace(tzinfo=timezone)


def process_due_reminders(now=None):
    config = current_app.config
    if not config.get('EMAIL_USER') or not config.get('EMAIL_PASS'):
        return 0

    timezone = ZoneInfo(config['TIMEZONE'])
    now = now or datetime.now(timezone)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone)
    else:
        now = now.astimezone(timezone)

    reminder_hour = config['APPOINTMENT_REMINDER_HOUR']
    max_attempts = config['APPOINTMENT_REMINDER_MAX_ATTEMPTS']
    retry_interval = config.get('APPOINTMENT_REMINDER_RETRY_MINUTES', 15)
    retry_before = now - timedelta(minutes=retry_interval)
    attempted_at = now.strftime('%Y-%m-%d %H:%M:%S')
    retry_before_text = retry_before.strftime('%Y-%m-%d %H:%M:%S')
    reminders_sent = 0

    for appointment in MessageRepository.get_reminder_candidates(max_attempts):
        appointment_datetime = _parse_appointment_datetime(
            appointment['fecha_cita'], timezone
        )
        if (
            appointment_datetime is None
            or appointment_datetime.date() != now.date()
            or now.hour < reminder_hour
            or appointment_datetime <= now
        ):
            continue

        claimed = MessageRepository.claim_reminder(
            appointment['id'],
            attempted_at,
            retry_before_text,
            max_attempts,
        )
        if not claimed:
            continue

        try:
            result = EmailService.send_appointment_reminder(
                patient_name=appointment['nombre'],
                patient_email=appointment['email'],
                appointment_date=appointment['fecha_cita'],
                modality=appointment['modalidad']
            )
        except (smtplib.SMTPException, OSError, TimeoutError):
            logger.exception(
                'Fallo el envio del recordatorio para la cita %s.',
                appointment['id']
            )
            continue

        if result['simulated']:
            logger.error(
                'No se envio el recordatorio para la cita %s: SMTP no esta configurado.',
                appointment['id']
            )
            continue

        if MessageRepository.mark_reminder_sent(appointment['id'], attempted_at):
            reminders_sent += 1
        else:
            logger.warning(
                'Se envio el recordatorio de la cita %s, pero no se pudo registrar '
                'el envio porque la cita ya no estaba pendiente.',
                appointment['id']
            )

    return reminders_sent
