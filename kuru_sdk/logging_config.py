import logging
import sys

# Configure the root logger
def configure_logging(level=logging.INFO):
    """
    Configure the module logger with the specified log level.
    
    Args:
        level: The logging level (default: logging.INFO)
    """

    logger = logging.getLogger(__name__)

    # Configure the root logger
    logger.setLevel(level)
    logger.addHandler(logging.NullHandler())

# Function to get a logger for a specific module
def get_logger(name):
    """
    Get a logger for a specific module.
    
    Args:
        name: The name of the module
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)