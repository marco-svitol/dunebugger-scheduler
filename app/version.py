"""
Version information for dunebugger-scheduler.

This file is automatically updated by CI/CD workflows.
The version follows semantic versioning (MAJOR.MINOR.PATCH).
"""

import os

# Default version - will be overridden during Docker build
__version__ = "0.1.0"
__build__ = "dev"
__commit__ = "unknown"

# Try to read version from environment variables (set during Docker build)
__version__ = os.environ.get("APP_VERSION", __version__)
__build__ = os.environ.get("APP_BUILD", __build__)
__commit__ = os.environ.get("APP_COMMIT", __commit__)


def get_version_info():
    """Return a dictionary with complete version information."""
    return {
        "version": __version__,
        "build": __build__,
        "commit": __commit__,
        "full_version": f"{__version__}-{__build__}+{__commit__[:7]}" if __commit__ != "unknown" else f"{__version__}-{__build__}"
    }


def get_version_string():
    """Return a formatted version string."""
    info = get_version_info()
    return info["full_version"]
