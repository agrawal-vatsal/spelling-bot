import sys
from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Configures the loguru global logger for clean, structured console output.

    Removes default handlers and adds a formatted stderr sink at the specified level.
    """
    # Remove loguru's default handler to avoid duplicated logs
    logger.remove()

    # Define a clean, high-visibility layout for runtime debugging
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level:7}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Add standard error sink
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=log_format,
        colorize=True,
    )

    logger.info(f"Logging initialized at level: {level.upper()}")