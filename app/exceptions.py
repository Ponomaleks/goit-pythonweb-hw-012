from fastapi import HTTPException, status

"""Application-specific exceptions."""


class ApplicationError(Exception):
    """Base class for all application exceptions."""

    pass


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""

    pass


class UserAlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "A user with this email already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenError(HTTPException):
    def __init__(self, detail: str = "Invalid access token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class UserNotFoundError(HTTPException):
    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ContactNotFoundError(ApplicationError):
    """Raised when a contact cannot be found."""

    pass


class ContactAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a contact with a duplicate email."""

    pass


class ValidationError(ApplicationError):
    """Raised when a request contains invalid data."""

    pass
