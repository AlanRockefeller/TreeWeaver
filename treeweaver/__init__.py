# TreeWeaver Application Package

# Make key components easily accessible from the treeweaver package
# For example, if you have a central settings manager:
from .config import settings_manager

__all__ = [
    'settings_manager',
    # Add other core components here as they are developed, e.g.:
    # 'MainWindow', 
    # 'core_function_x',
]

# You might also want to set up a top-level logger here if not done elsewhere,
# or define application-wide constants.
import logging
# Set up a default null handler for the library to avoid 'No handler found' warnings
# if the application using this library doesn't configure logging.
# The application itself (treeweaver.py) will configure the actual handlers.
logging.getLogger(__name__).addHandler(logging.NullHandler())
