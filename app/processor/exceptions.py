class ProcessorError(Exception):
    """Base exception for all processor-related errors."""


class DocumentNotFoundError(ProcessorError):
    """Raised when a document cannot be found in the database."""


class UnsupportedStorageDiskError(ProcessorError):
    """Raised when a document uses an unsupported storage disk type."""


class FileReadError(ProcessorError):
    """Raised when a file cannot be read from disk."""
