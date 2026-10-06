import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template, current_app
from ..utils.validators import sanitize

class EmailService:
    """Service handling email rendering and SMTP dispatching."""

    @classmethod
    def send_appointment_confirmation(cls, patient_name, patient_email, appointment_date, modality):
        """
        Renders HTML email from Jinja2 template and delivers via SMTP or logs simulation.
        """
        config = current_app.config
        sender_email = config.get('EMAIL_USER', '')
        sender_password = config.get('EMAIL_PASS', '')
        smtp_host = config.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = config.get('SMTP_PORT', 587)
        clinic_name = config.get('CLINIC_NAME', 'Zumaikira Bailey Psicóloga')
        clinic_title = config.get('CLINIC_TITLE', 'PSICOLOGA - C.I.P. 8362')
        clinic_phone = config.get('CLINIC_PHONE', '+507 6235-281')
        clinic_address = config.get('CLINIC_ADDRESS', 'Atlantic Plaza, 1er piso, local 127, oficina #224')
        clinic_email = config.get('CLINIC_EMAIL', 'Zumaikirabailey98@gmail.com')

        # Render HTML template with sanitized values
        html_content = render_template(
            'emails/appointment_confirmation.html',
            clinic_name=clinic_name,
            clinic_title=clinic_title,
            patient_name=sanitize(patient_name),
            appointment_date=sanitize(appointment_date),
            modality=sanitize(modality),
            clinic_address=clinic_address,
            clinic_phone=clinic_phone
        )

        if not sender_email or not sender_password:
            print("\n" + "=" * 50)
            print("SIMULACION DE ENVIO DE CORREO")
            print(f"Para: {patient_email}")
            print(f"Asunto: Confirmacion de Cita - {clinic_name}")
            print(f"Fecha: {appointment_date}")
            print(f"Modalidad: {modality}")
            print("=" * 50 + "\n")
            return {'sent': False, 'simulated': True}

        # Real SMTP dispatch
        email_msg = MIMEMultipart("alternative")
        email_msg["Subject"] = f"Confirmacion de Cita Psicologica - {clinic_name}"
        email_msg["From"] = f"{clinic_name} <{sender_email}>"
        email_msg["Reply-To"] = clinic_email
        email_msg["To"] = patient_email
        email_msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(email_msg)
        server.quit()
        print(f"[EmailService] Correo real enviado exitosamente a {patient_email}")
        return {'sent': True, 'simulated': False}
