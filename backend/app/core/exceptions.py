"""Domain-level exceptions, translated to HTTP responses at the API boundary."""


class TruthOSError(Exception):
    """Base class for all application-raised errors."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(TruthOSError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)


class UnauthorizedError(TruthOSError):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, status_code=401)


class ForbiddenError(TruthOSError):
    def __init__(self, message: str = "Not authorized") -> None:
        super().__init__(message, status_code=403)


class ConflictError(TruthOSError):
    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, status_code=409)


class AgentExecutionError(TruthOSError):
    """Raised when an agent exhausts its retry policy without a usable result."""

    def __init__(self, agent_name: str, message: str) -> None:
        super().__init__(f"[{agent_name}] {message}", status_code=502)
        self.agent_name = agent_name


class RetrievalError(TruthOSError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)
