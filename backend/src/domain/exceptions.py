"""Domain exceptions - Business rule violations and domain errors."""


class DomainError(Exception):
    """Base exception for all domain errors."""


class SSHConnectionError(DomainError):
    """Cannot establish connection to the remote server."""


class BackupError(DomainError):
    """Backup generation or transfer failed."""


class DatabaseNotFoundError(DomainError):
    """Requested database does not exist on the server."""
