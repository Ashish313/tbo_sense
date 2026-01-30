from enum import Enum

class LogLevels(Enum):
    Info = "INFO"
    Error = "ERROR"
    Warning = "WARNING"
    Debug = "DEBUG"

def generate_app_log(api_name, log_level, message, start_time=None, reference_id=None, user_id=None, **kwargs):
    print(f"[{log_level.value}] {api_name}: {message}")
