"""
Repository management functionality.
"""
import os
import sys
import tempfile
import shutil
import importlib.util
import types
from typing import Dict, Optional, Any, Union
import git

# Global cache of imported repositories
_REPO_CACHE: Dict[str, Any] = {}

def _get_repo_url(repo_path: str) -> str:
    """Convert repo path to URL with auth token."""
    from .auth import get_token
    
    # If it's already a full URL
    if repo_path.startswith("http"):
        base_url = repo_path
    else:
        # Assume it's in the format username/repo_name
        base_url = f"https://github.com/{repo_path}.git"
    
    # Add token for authentication
    token = get_token()
    auth_url = base_url.replace("https://", f"https://{token}@")
    
    return auth_url

def _get_local_path(repo_name: str) -> str:
    """Get local path for storing the repository."""
    # Create a unique path in the temp directory
    base_dir = os.path.join(tempfile.gettempdir(), "gri")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, repo_name)

def _clone_repo(repo_path: str, branch: str = "main") -> str:
    """Clone a repository to local storage."""
    # Parse repo name from path
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    # Get URLs and paths
    auth_url = _get_repo_url(repo_path)
    local_path = _get_local_path(repo_name)
    
    # Remove existing directory if it exists
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    
    # Clone the repository
    git.Repo.clone_from(auth_url, local_path, branch=branch)
    
    return local_path

def _create_module(name: str, path: str) -> types.ModuleType:
    """Create a module object from a file or directory."""
    if os.path.isfile(path) and path.endswith(".py"):
        # It's a Python file
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module {name} from {path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    elif os.path.isdir(path):
        # It's a directory - create a package
        module = types.ModuleType(name)
        sys.modules[name] = module
        
        # Set the module's __path__ attribute to make it a package
        module.__path__ = [path]
        
        # Add __file__ attribute
        module.__file__ = os.path.join(path, "__init__.py")
        
        # Process all Python files in the directory
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # Skip hidden files and directories
            if item.startswith("__") and item.endswith("__"):
                continue
                
            if item.endswith(".py"):
                # It's a Python file
                module_name = item[:-3]
                submodule = _create_module(f"{name}.{module_name}", item_path)
                setattr(module, module_name, submodule)
            elif os.path.isdir(item_path) and not item.startswith("."):
                # It's a subdirectory
                subpackage = _create_module(f"{name}.{item}", item_path)
                setattr(module, item, subpackage)
                
        return module
    
    raise ValueError(f"Path {path} is neither a Python file nor a directory")

def import_repo(repo_path: str, branch: str = "main") -> types.ModuleType:
    """
    Import a GitHub repository as a Python module.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        branch: The branch to import (default: "main")
        
    Returns:
        A module object representing the repository.
    """
    # Check if already in cache
    cache_key = f"{repo_path}:{branch}"
    if cache_key in _REPO_CACHE:
        return _REPO_CACHE[cache_key]
    
    # Clone the repository
    local_path = _clone_repo(repo_path, branch)
    
    # Parse repo name from path for the module name
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    # Add the repository directory to sys.path temporarily
    sys.path.insert(0, os.path.dirname(local_path))
    
    try:
        # Import the repository as a module
        module = _create_module(repo_name, local_path)
        
        # Store in cache
        _REPO_CACHE[cache_key] = module
        
        return module
    finally:
        # Remove the directory from sys.path
        if os.path.dirname(local_path) in sys.path:
            sys.path.remove(os.path.dirname(local_path))

def update_repo(repo_path: str, branch: str = "main") -> types.ModuleType:
    """
    Update a previously imported GitHub repository.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        branch: The branch to update (default: "main")
        
    Returns:
        The updated module object representing the repository.
    """
    # Parse repo name from path
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    local_path = _get_local_path(repo_name)
    
    # Check if repository exists locally
    if not os.path.exists(local_path):
        return import_repo(repo_path, branch)
    
    # Update the local repository
    repo = git.Repo(local_path)
    
    # Update remote URL with token
    auth_url = _get_repo_url(repo_path)
    for remote in repo.remotes:
        if remote.name == "origin":
            remote.set_url(auth_url)
    
    # Pull changes
    repo.git.checkout(branch)
    repo.git.pull()
    
    # Clear the repository from cache
    cache_key = f"{repo_path}:{branch}"
    if cache_key in _REPO_CACHE:
        del _REPO_CACHE[cache_key]
    
    # Reimport the repository
    return import_repo(repo_path, branch)