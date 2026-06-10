import os
import logging
from typing import Optional
from src.utils.constants import current_datetime_readable

# Default logging configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def get_log_level() -> int:
    """Get logging level from environment variable or default"""
    level_str = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    return level_mapping.get(level_str, logging.INFO)

def get_log_format() -> str:
    """Get logging format from environment variable or default"""
    return os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT)

def should_log_to_console() -> bool:
    """Check if console logging is enabled"""
    return os.getenv("LOG_TO_CONSOLE", "false").lower() in ("true", "1", "yes")

def should_log_to_file() -> bool:
    """Check if file logging is enabled"""
    return os.getenv("LOG_TO_FILE", "true").lower() in ("true", "1", "yes")

def get_log_directory() -> str:
    """Get log directory from environment or default"""
    return os.getenv("LOG_DIRECTORY", "logs")

def configure_logging(
    custom_level: Optional[int] = None,
    custom_format: Optional[str] = None,
    force_console: bool = False
) -> None:
    """
    Configure centralized logging for the entire application
    
    Args:
        custom_level: Override log level if needed
        custom_format: Override log format if needed
        force_console: Force console output regardless of env settings (also disables file logging for containers)
    """
    
    # Get configuration
    log_level = custom_level or get_log_level()
    log_format = custom_format or get_log_format()
    log_to_console = should_log_to_console() or force_console
    # Disable file logging when force_console is True (running in container/AgentCore)
    log_to_file = should_log_to_file() and not force_console
    log_directory = get_log_directory()
    
    # Only create log directory if file logging is enabled
    if log_to_file:
        os.makedirs(log_directory, exist_ok=True)
    
    # Create handlers list
    handlers = []
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)
    
    # File handler with general app name
    if log_to_file:
        log_file_path = os.path.join(
            log_directory,
            f"agent_{current_datetime_readable}.log"
        ).replace(":", "_")
        
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    # Log the configuration
    logger = logging.getLogger("agent")
    logger.info("Centralized logging configured for application")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Console logging: {log_to_console}")
    logger.info(f"File logging: {log_to_file}")
    if log_to_file:
        logger.info(f"Log file: {log_file_path}")

# Environment variable examples for .env file:
"""
# Logging Configuration
LOG_LEVEL=DEBUG                # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_CONSOLE=true            # true/false - Enable console output
LOG_TO_FILE=true               # true/false - Enable file logging
LOG_DIRECTORY=logs             # Directory for log files
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
"""
