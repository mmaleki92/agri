"""
Import Python modules directly from GitHub repositories.
"""

from .auth import authenticate, get_token
from .repo_manager import import_repo, update_repo

__version__ = "0.1.0"
__all__ = ["authenticate", "import_repo", "update_repo"]