import logging
import sys


class Log:
    """Centralized logging with structured format."""

    _logger: logging.Logger = logging.getLogger("bioreport")

    @classmethod
    def configure(cls, log_level: str) -> None:
        """Configure the logger with the specified level and stdout handler."""
        cls._logger.setLevel(log_level.upper())
        if not cls._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            cls._logger.addHandler(handler)

    @classmethod
    def info(cls, message: str, **kwargs: object) -> None:
        """Log an info message."""
        cls._logger.info(message, extra=kwargs)

    @classmethod
    def error(cls, message: str, **kwargs: object) -> None:
        """Log an error message."""
        cls._logger.error(message, extra=kwargs)

    @classmethod
    def warning(cls, message: str, **kwargs: object) -> None:
        """Log a warning message."""
        cls._logger.warning(message, extra=kwargs)

    @classmethod
    def debug(cls, message: str, **kwargs: object) -> None:
        """Log a debug message."""
        cls._logger.debug(message, extra=kwargs)
