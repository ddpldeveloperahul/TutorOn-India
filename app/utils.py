from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import re

def standard_response(success=True, message="", data=None, errors=None, status_code=status.HTTP_200_OK):
    """
    Standardized API response structure for TutorOn India.
    """
    payload = {
        "success": success,
        "message": message,
        "data": data if data is not None else {},
        "errors": errors if errors is not None else {}
    }
    return Response(payload, status=status_code)

def custom_exception_handler(exc, context):
    """
    Custom exception handler to format errors consistently.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "success": False,
            "message": "An error occurred during request processing.",
            "data": {},
            "errors": response.data
        }
        response.data = custom_data

    return response

def validate_youtube_url(url):
    """
    Validates if a given URL is a valid YouTube video URL.
    """
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+'
    return bool(re.match(youtube_regex, url))

def validate_zoom_url(url):
    """
    Validates if a given URL is a valid Zoom meeting link.
    """
    zoom_regex = r'^(https?://)?([a-zA-Z0-9-]+\.)?zoom\.us/j/[0-9]+'
    return bool(re.match(zoom_regex, url))

def validate_google_meet_url(url):
    """
    Validates if a given URL is a valid Google Meet link.
    """
    meet_regex = r'^(https?://)?meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}'
    return bool(re.match(meet_regex, url))

def log_audit_action(user, action, target_model="", target_id="", ip_address="127.0.0.1", details=None):
    """
    Helper function to log administrative and user security actions.
    """
    from app.models import AuditLog
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        target_model=target_model,
        target_id=str(target_id),
        ip_address=ip_address,
        details=details or {}
    )
