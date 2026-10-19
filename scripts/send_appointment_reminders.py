import logging
import signal
import threading

from backend import create_app
from backend.services.appointment_reminder_service import process_due_reminders


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )
    app = create_app()
    stop_event = threading.Event()

    def request_stop(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    if not app.config.get('EMAIL_USER') or not app.config.get('EMAIL_PASS'):
        app.logger.warning(
            'Recordatorios deshabilitados: configura EMAIL_USER y EMAIL_PASS en .env.'
        )

    app.logger.info(
        'Worker de recordatorios iniciado. Zona horaria: %s; hora de envio: %02d:00.',
        app.config['TIMEZONE'],
        app.config['APPOINTMENT_REMINDER_HOUR']
    )
    while not stop_event.is_set():
        with app.app_context():
            sent_count = process_due_reminders()
            if sent_count:
                app.logger.info('Recordatorios enviados: %d.', sent_count)
        stop_event.wait(60)


if __name__ == '__main__':
    main()
