"""
Repository browsing functionality with lazy loading.
"""
import os
import sys
import tempfile
import shutil
import importlib.util
import types
from typing import Dict, Optional, Any, Union, List, Callable
import git
from tqdm import tqdm

# Global cache of imported repositories
_REPO_CACHE: Dict[str, Any] = {}
_REPO_PATHS: Dict[str, str] = {}  # Store local paths of repositories


class LazyModule:
    """A module that lazily loads its contents when accessed."""
    
    def __init__(self, name: str, path: str):
        self.__name__ = name
        self.__path__ = path
        self.__loaded__ = False
        self.__dict__["_children"] = {}
        
        # Scan directory structure but don't execute code
        self._scan_structure()
    
    def _scan_structure(self):
        """Scan the directory structure without executing code."""
        path = self.__path__
        
        if os.path.isfile(path) and path.endswith(".py"):
            # It's a Python file - we'll load it when accessed
            pass
        elif os.path.isdir(path):
            # Scan directory for files and subdirectories
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                # Skip hidden files and directories
                if item.startswith("."):
                    continue
                
                # Skip __pycache__ and other special directories
                if item.startswith("__") and item.endswith("__"):
                    continue
                
                if item.endswith(".py"):
                    # It's a Python file
                    module_name = item[:-3]
                    self._children[module_name] = item_path
                elif os.path.isdir(item_path):
                    # It's a subdirectory
                    submodule_name = item
                    submodule = LazyModule(f"{self.__name__}.{submodule_name}", item_path)
                    self._children[submodule_name] = submodule
    
    def _load_module(self):
        """Fully load this module if it's a Python file."""
        if self.__loaded__:
            return
            
        path = self.__path__
        if os.path.isfile(path) and path.endswith(".py"):
            try:
                spec = importlib.util.spec_from_file_location(self.__name__, path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not load module {self.__name__} from {path}")
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[self.__name__] = module
                
                # Here's where we actually execute the module code
                spec.loader.exec_module(module)
                
                # Copy attributes from loaded module to this LazyModule
                for key, value in module.__dict__.items():
                    if not key.startswith("__"):
                        self.__dict__[key] = value
                        
                self.__loaded__ = True
            except Exception as e:
                print(f"Error loading module {self.__name__}: {e}")
                raise
    
    def __getattr__(self, name):
        """Lazily load modules or return child objects when accessed."""
        # If this is a file module, load it when any attribute is accessed
        if os.path.isfile(self.__path__) and self.__path__.endswith(".py"):
            self._load_module()
            if name in self.__dict__:
                return self.__dict__[name]
            raise AttributeError(f"Module {self.__name__} has no attribute {name}")
        
        # For directory modules, check if it's a child
        if name in self._children:
            child = self._children[name]
            
            # If child is a path string, it's a Python file that needs to be loaded
            if isinstance(child, str) and child.endswith(".py"):
                module = LazyModule(f"{self.__name__}.{name}", child)
                self._children[name] = module  # Cache the module
                return module
            
            # Otherwise it's already a LazyModule
            return child
            
        raise AttributeError(f"Module {self.__name__} has no attribute or submodule {name}")
    
    def __dir__(self):
        """List available attributes and submodules."""
        if os.path.isfile(self.__path__) and self.__path__.endswith(".py"):
            if not self.__loaded__:
                self._load_module()
            return list(self.__dict__.keys())
        else:
            return list(self._children.keys())
            
    def __repr__(self):
        if os.path.isfile(self.__path__):
            return f"<LazyModule '{self.__name__}' from '{self.__path__}'>"
        else:
            return f"<LazyPackage '{self.__name__}' from '{self.__path__}'>"


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
    base_dir = os.path.join(tempfile.gettempdir(), "agri")
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


def import_repo(repo_path: str, branch: str = "main", show_structure: bool = True) -> LazyModule:
    """
    Import a GitHub repository as a lazily-loaded module structure.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        branch: The branch to import (default: "main")
        show_structure: Whether to print the repository structure after importing
        
    Returns:
        A LazyModule object representing the repository.
    """
    # Check if already in cache
    cache_key = f"{repo_path}:{branch}"
    if cache_key in _REPO_CACHE:
        module = _REPO_CACHE[cache_key]
        print(f"✨ Using cached repository {repo_path} (branch: {branch})")
        
        if show_structure and cache_key in _REPO_PATHS:
            print("\n📂 Repository structure:")
            print(get_structure(_REPO_PATHS[cache_key]))
            
        return module
    
    # Clone the repository
    print(f"🚀 Importing repository {repo_path} (branch: {branch})...")
    local_path = _clone_repo(repo_path, branch)
    
    print(f"📦 Processing repository content...")
    with tqdm(total=100, desc="Building module structure", ascii=True) as pbar:
        # Parse repo name from path for the module name
        if "/" in repo_path:
            repo_name = repo_path.split("/")[-1]
        else:
            repo_name = repo_path
        
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        
        pbar.update(50)  # Update progress
        
        # Create lazy module for the repository
        module = LazyModule(repo_name, local_path)
        pbar.update(50)  # Update progress to 100%
        
        # Store in cache
        _REPO_CACHE[cache_key] = module
        _REPO_PATHS[cache_key] = local_path
        
        if show_structure:
            print("\n📂 Repository structure:")
            print(get_structure(local_path))
        
        return module


def get_structure(path: str, prefix: str = "", ignore_patterns: List[str] = None) -> str:
    """
    Get a string representation of the directory structure.
    
    Args:
        path: Path to the directory
        prefix: Prefix for the current line (used for recursion)
        ignore_patterns: List of patterns to ignore (e.g. [".git", "__pycache__"])
        
    Returns:
        A formatted string showing the directory structure
    """
    if ignore_patterns is None:
        ignore_patterns = [".git", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", "venv", "env", ".env"]
    
    if not os.path.exists(path):
        return f"{prefix}Path does not exist: {path}"
    
    if os.path.isfile(path):
        return f"{prefix}└── {os.path.basename(path)}"
    
    result = []
    
    if prefix == "":
        result.append(f"📁 {os.path.basename(path)}")
        prefix = "   "
    
    # Get all items in the directory
    items = [item for item in sorted(os.listdir(path)) 
             if not any(pattern in item for pattern in ignore_patterns)]
    
    # Process directories first, then files
    dirs = [item for item in items if os.path.isdir(os.path.join(path, item))]
    files = [item for item in items if os.path.isfile(os.path.join(path, item))]
    
    # Keep track of processed items
    total_items = len(dirs) + len(files)
    processed_items = 0
    
    # Process directories
    for i, item in enumerate(dirs):
        processed_items += 1
        item_path = os.path.join(path, item)
        
        if processed_items == total_items:  # Last item
            result.append(f"{prefix}└── 📁 {item}")
            result.append(get_structure(item_path, prefix + "    ", ignore_patterns))
        else:
            result.append(f"{prefix}├── 📁 {item}")
            result.append(get_structure(item_path, prefix + "│   ", ignore_patterns))
    
    # Process files
    for i, item in enumerate(files):
        processed_items += 1
        
        if processed_items == total_items:  # Last item
            if item.endswith(".py"):
                result.append(f"{prefix}└── 🐍 {item}")
            elif item.endswith((".jpg", ".png", ".gif", ".bmp", ".jpeg")):
                result.append(f"{prefix}└── 🖼️ {item}")
            elif item.endswith((".json", ".yaml", ".yml", ".toml", ".xml")):
                result.append(f"{prefix}└── 📋 {item}")
            elif item.endswith((".md", ".txt", ".rst")):
                result.append(f"{prefix}└── 📝 {item}")
            else:
                result.append(f"{prefix}└── 📄 {item}")
        else:
            if item.endswith(".py"):
                result.append(f"{prefix}├── 🐍 {item}")
            elif item.endswith((".jpg", ".png", ".gif", ".bmp", ".jpeg")):
                result.append(f"{prefix}├── 🖼️ {item}")
            elif item.endswith((".json", ".yaml", ".yml", ".toml", ".xml")):
                result.append(f"{prefix}├── 📋 {item}")
            elif item.endswith((".md", ".txt", ".rst")):
                result.append(f"{prefix}├── 📝 {item}")
            else:
                result.append(f"{prefix}├── 📄 {item}")
    
    return "\n".join(result)


def update_repo(repo_path: str, branch: str = "main", show_structure: bool = True) -> LazyModule:
    """
    Update a previously imported GitHub repository.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        branch: The branch to update (default: "main")
        show_structure: Whether to print the repository structure after updating
        
    Returns:
        The updated LazyModule object representing the repository.
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
        print(f"⚠️ Repository {repo_path} not found locally. Cloning fresh copy...")
        return import_repo(repo_path, branch, show_structure)
    
    print(f"🔄 Updating repository {repo_path} (branch: {branch})...")
    
    try:
        # Update the local repository
        repo = git.Repo(local_path)
        
        # Update remote URL with token
        auth_url = _get_repo_url(repo_path)
        origin = repo.remote(name="origin")
        origin.set_url(auth_url)
        
        # Pull changes with progress bar
        with tqdm(total=100, desc=f"Updating {repo_name}", ascii=True) as pbar:
            # Checkout branch
            repo.git.checkout(branch)
            pbar.update(30)
            
            # Check for changes first
            repo.git.fetch()
            pbar.update(30)
            
            # Show progress during pull
            result = repo.git.pull()
            pbar.update(40)
            
            if "Already up to date" in result:
                print(f"✅ Repository {repo_path} is already up to date")
            else:
                print(f"✅ Repository {repo_path} updated successfully")
        
        # Clear the repository from cache
        cache_key = f"{repo_path}:{branch}"
        if cache_key in _REPO_CACHE:
            del _REPO_CACHE[cache_key]
        
        # Reimport the repository
        return import_repo(repo_path, branch, show_structure)
    except git.exc.GitCommandError as e:
        print(f"❌ Error updating repository: {e}")
        print("⚠️ Attempting to clone fresh copy...")
        shutil.rmtree(local_path, ignore_errors=True)
        return import_repo(repo_path, branch, show_structure)