"""Service-level errors with an HTTP status attached.

Messages are written for the end user (README §3: clear error messages) and
never reveal secrets.
"""


class ServiceError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BadRequest(ServiceError):
    status_code = 400


class Unauthorized(ServiceError):
    status_code = 401


class Forbidden(ServiceError):
    status_code = 403


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class Locked(ServiceError):
    status_code = 423


class ServiceUnavailable(ServiceError):
    status_code = 503
