from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_notification_email(subject, message, recipient_list):
    """
    Celery task to send asynchronous notification emails.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return f"Email sent successfully to {recipient_list}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

@shared_task
def send_class_reminder_emails():
    """
    Celery periodic task to send upcoming class reminders to students.
    """
    from app.models import ClassContent, Enrollment
    now = timezone.now()
    upcoming = now + timedelta(minutes=30)
    
    classes = ClassContent.objects.filter(scheduled_at__gte=now, scheduled_at__lte=upcoming)
    reminders_sent = 0

    for cls in classes:
        enrollments = Enrollment.objects.filter(batch=cls.batch, status='ACTIVE')
        recipients = [e.student.email for e.student in enrollments if e.student.email]
        if recipients:
            send_mail(
                subject=f"Class Reminder: {cls.title}",
                message=f"Your class '{cls.title}' in batch '{cls.batch.title}' starts in 30 minutes at {cls.scheduled_at}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True
            )
            reminders_sent += len(recipients)

    return f"Sent {reminders_sent} class reminder emails."

@shared_task
def cleanup_expired_tokens():
    """
    Celery task to flush blacklisted JWT tokens.
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    OutstandingToken.objects.filter(expires_at__lt=timezone.now()).delete()
    return "Expired JWT tokens cleaned up."
