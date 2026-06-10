from datetime import datetime

# Get current datetime in ISO format (standard, clean format for prompts)
def get_current_datetime_iso():
    return datetime.now().isoformat()

# Get current datetime in a more human-readable format
current_datetime_readable = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

def get_current_datetime_readable():
    return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
