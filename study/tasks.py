import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .views import NotificationService

logger = logging.getLogger(__name__)

@shared_task(name="study.tasks.send_async_email")
def send_async_email(subject, message, recipient_list, from_email=None):
    """
    Asynchronously send emails using Celery worker.
    """
    from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tutoron.in')
    try:
        sent = send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return {"status": "success", "sent": sent}
    except Exception as exc:
        logger.error(f"Error sending async email to {recipient_list}: {exc}")
        return {"status": "error", "error": str(exc)}

@shared_task(name="study.tasks.send_scheduled_class_reminders")
def send_scheduled_class_reminders(window_minutes=60):
    """
    Celery Beat task to periodically check for upcoming classes and dispatch reminders.
    Sends reminders for classes starting in the next `window_minutes` minutes.
    """
    try:
        count = NotificationService.send_upcoming_class_reminders(window_minutes=window_minutes)
        logger.info(f"Class reminders dispatched: {count}")
        return {"status": "success", "reminders_sent": count}
    except Exception as exc:
        logger.error(f"Error running send_scheduled_class_reminders: {exc}")
        return {"status": "error", "error": str(exc)}
