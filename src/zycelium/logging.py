import logging
import sys
from pathlib import Path
from typing import Optional

logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("tzlocal").setLevel(logging.WARNING)


def get_logger(
    name: str, level: int = logging.INFO, log_file: Optional[Path] = None
) -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:  # pragma: no cover
        # Return if logger is already configured
        return logger

    logger.setLevel(level)
    logger.propagate = False  # Prevent duplicate logs
    formatter = logging.Formatter(
        "[%(asctime)s] [%(process)d] [%(name)s:%(lineno)d] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:  # pragma: no cover
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
