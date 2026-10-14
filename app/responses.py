from flask import jsonify, request
from pydantic import ValidationError


def read_json_object():
    """Return (body, error_response). error_response is set when the body is unusable."""
    if not request.is_json:
        return None, (
            jsonify(
                {
                    "error": "Unsupported content type",
                    "message": "Request body must be sent as application/json.",
                }
            ),
            415,
        )

    body = request.get_json(silent=True)
    if body is None:
        return None, (
            jsonify(
                {
                    "error": "Malformed JSON",
                    "message": "Request body is not valid JSON. Check for syntax errors.",
                }
            ),
            400,
        )

    if not isinstance(body, dict):
        return None, (
            jsonify(
                {
                    "error": "Invalid payload",
                    "message": "Request body must be a JSON object.",
                }
            ),
            400,
        )

    return body, None


def validation_error_response(error: ValidationError):
    details = {
        ".".join(str(part) for part in err["loc"]) or "body": err["msg"]
        for err in error.errors()
    }
    message = "; ".join(f"{field}: {msg}" for field, msg in details.items())
    return (
        jsonify(
            {
                "error": "Validation error",
                "message": message,
            }
        ),
        422,
    )
