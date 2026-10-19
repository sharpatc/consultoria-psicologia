import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zoneinfo import ZoneInfo
from flask import render_template, current_app
from ..utils.validators import sanitize


class EmailService:
    """Service handling email rendering and SMTP dispatching."""

    @classmethod
    def send_appointment_confirmation(
        cls, patient_name, patient_email, appointment_date, modality
    ):
        return cls._send_appointment_email(
            patient_name,
            patient_email,
            appointment_date,
            modality,
            is_reminder=False
        )

    @classmethod
    def send_appointment_reminder(
        cls, patient_name, patient_email, appointment_date, modality
    ):
        return cls._send_appointment_email(
            patient_name,
            patient_email,
            appointment_date,
            modality,
            is_reminder=True
        )

    @classmethod
    def _send_appointment_email(
        cls, patient_name, patient_email, appointment_date, modality, is_reminder
    ):
        config = current_app.config
        sender_email = config.get('EMAIL_USER', '')
        sender_password = config.get('EMAIL_PASS', '')
        smtp_host = config.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = config.get('SMTP_PORT', 587)
        clinic_name = config.get('CLINIC_NAME', 'PsicoEmocional')
        clinic_title = config.get('CLINIC_TITLE', 'Psicologia y bienestar emocional')
        clinic_phone = config.get('CLINIC_PHONE', '+507 6235-281')
        clinic_address = config.get(
            'CLINIC_ADDRESS',
            'Atlantic Plaza, 1er piso, local 127, oficina #224'
        )
        clinic_email = config.get('CLINIC_EMAIL', 'Zumaikirabailey98@gmail.com')
        try:
            appointment_datetime = datetime.fromisoformat(appointment_date)
            timezone = ZoneInfo(config.get('TIMEZONE', 'America/Panama'))
            if appointment_datetime.tzinfo:
                appointment_datetime = appointment_datetime.astimezone(timezone)
            weekdays = (
                'lunes', 'martes', 'miercoles', 'jueves',
                'viernes', 'sabado', 'domingo'
            )
            formatted_appointment_date = (
                f"{weekdays[appointment_datetime.weekday()]}, "
                f"{appointment_datetime.strftime('%d/%m/%Y a las %H:%M')}"
            )
        except ValueError:
            formatted_appointment_date = appointment_date
        subject_prefix = 'Recordatorio de cita' if is_reminder else 'Confirmacion de cita'
        heading = 'Recordatorio de tu cita' if is_reminder else 'Cita confirmada'
        introduction = (
            'Te recordamos que hoy tienes una cita. Te esperamos.'
            if is_reminder
            else 'Nos complace confirmarte que tu cita ha sido agendada con exito.'
        )

        html_content = render_template(
            'emails/appointment_confirmation.html',
            clinic_name=clinic_name,
            clinic_title=clinic_title,
            patient_name=sanitize(patient_name),
            appointment_date=sanitize(formatted_appointment_date),
            modality=sanitize(modality),
            clinic_address=clinic_address,
            clinic_phone=clinic_phone,
            email_heading=heading,
            email_introduction=introduction
        )
        plain_content = (
            f"Hola, {patient_name}.\n\n{introduction}\n\n"
            f"Fecha y hora: {formatted_appointment_date}\n"
            f"Modalidad: {modality}\n"
            f"Ubicacion: {clinic_address}\n\n"
            f"Si necesitas comunicarte, llama al {clinic_phone}."
        )

        if not sender_email or not sender_password:
            print(
                f"[EmailService] SMTP no configurado; no se envio '{subject_prefix}' "
                f"a {patient_email}."
            )
            return {'sent': False, 'simulated': True}

        email_msg = MIMEMultipart('alternative')
        email_msg['Subject'] = f'{subject_prefix} - {clinic_name}'
        email_msg['From'] = f'{clinic_name} <{sender_email}>'
        email_msg['Reply-To'] = clinic_email
        email_msg['To'] = patient_email
        email_msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
        email_msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(sender_email, sender_password)
            server.send_message(email_msg)

        print(f"[EmailService] '{subject_prefix}' enviado a {patient_email}.")
        return {'sent': True, 'simulated': False}
