import os
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "").lower()

# Logging Configuration
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO").upper(),
    "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    "to_console": os.getenv("LOG_TO_CONSOLE", "false").lower() in ("true", "1", "yes"),
    "to_file": os.getenv("LOG_TO_FILE", "true").lower() in ("true", "1", "yes"),
    "directory": os.getenv("LOG_DIRECTORY", "logs")
}

AWS_CONFIG = {
    "region_name": os.getenv("AWS_REGION", "us-east-1"),
}
