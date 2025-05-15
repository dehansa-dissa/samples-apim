import logging
import sys

def setup_logger(name: str = "api_mock_generator"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Console handler with different log levels
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    # Formatter for log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch.setFormatter(formatter)

    # Avoid adding multiple handlers if already added
    if not logger.hasHandlers():
        logger.addHandler(ch)

    return logger

logger = setup_logger()
