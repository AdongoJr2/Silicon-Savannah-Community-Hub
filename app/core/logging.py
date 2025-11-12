"""
Structured logging configuration using loguru.
"""
import sys
from loguru import logger
from app.core.config import settings

# Remove default handler
logger.remove()

# Add custom handler with structured format
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
    colorize=True,
)

# Add file handler for production
if settings.ENVIRONMENT == "production":
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
    )

# Export configured logger
__all__ = ["logger"]
