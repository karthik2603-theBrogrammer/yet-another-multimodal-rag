import logging

# Configure the logger
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log message format
    datefmt="%Y-%m-%d %H:%M:%S",  # Date and time format
    handlers=[
        logging.StreamHandler()  # Log to console
    ]
)

# Create a logger instance
logger = logging.getLogger(__name__)