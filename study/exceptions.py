import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            exc = DRFValidationError(detail=exc.message_dict)
        elif hasattr(exc, 'messages'):
            exc = DRFValidationError(detail=exc.messages)
        else:
            exc = DRFValidationError(detail=str(exc))

    response = exception_handler(exc, context)

    if response is not None:
        errors = {}
        message = "An error occurred."
        if isinstance(response.data, dict):
            if "detail" in response.data:
                message = str(response.data["detail"])
                errors = {"detail": [message]}
            else:
                message = "Validation failed"
                errors = response.data
        elif isinstance(response.data, list):
            message = "Validation failed"
            errors = {"non_field_errors": response.data}
        else:
            message = str(response.data)
            errors = {"error": [message]}

        response.data = {
            "success": False,
            "message": message,
            "errors": errors
        }
        return response

    logger.exception("Unhandled server exception: %s", exc)
    return Response(
        {
            "success": False,
            "message": "Internal server error. Please try again later.",
            "errors": {"server": ["An unexpected error occurred."]}
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
