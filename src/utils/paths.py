import sys
import os
from pathlib import Path

def get_app_root() -> Path:
    """
    Returns the root directory of the application.
    - If running as a frozen executable (Nuitka/PyInstaller), returns the directory of the executable.
    - If running as a script, returns the project root (3 levels up from this file: src/utils/paths.py -> src/utils/ -> src/ -> project_root/).
    """
    if getattr(sys, 'frozen', False):
        # Path to the .exe directory
        return Path(sys.executable).parent
    else:
        # Path to the project root relative to this file
        # src/utils/paths.py -> 3 levels up
        return Path(__file__).resolve().parent.parent.parent

def get_config_dir() -> Path:
    """Returns the path to the config directory."""
    config_dir = get_app_root() / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir

def get_data_dir() -> Path:
    """Returns the path to the data directory."""
    data_dir = get_app_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_resources_dir() -> Path:
    """Returns the path to the resources directory."""
    return get_app_root() / "resources"

def get_logs_dir() -> Path:
    """Returns the path to the logs directory."""
    logs_dir = get_app_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir
