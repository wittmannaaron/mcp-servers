import sys
from loguru import logger
from src.core.simple_config import settings

def setup_logging():
    """
    Set up Loguru logger with configured settings.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    if settings.log_to_file:
        logger.add(
            settings.log_file_path,
            rotation=settings.log_file_rotation,
            retention=settings.log_file_retention,
            level=settings.log_level.upper(),
            format="{time} {level} {message}",
            enqueue=True,  # Make logging thread-safe
            backtrace=True,
            diagnose=True
        )
    logger.info("Logging configured.")