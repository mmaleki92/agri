"""
Import Python modules directly from GitHub repositories.
"""

from .auth import authenticate, get_token
from .repo_manager import import_repo, update_repo, get_repo_structure

__version__ = "0.1.1"
__all__ = ["authenticate", "import_repo", "update_repo"]