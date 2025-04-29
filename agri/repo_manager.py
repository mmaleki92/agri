"""
Repository management functionality.
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


def import_repo(repo_path: str, branch: str = "main", show_structure: bool = True) -> types.ModuleType:
    """
    Import a GitHub repository as a Python module.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        branch: The branch to import (default: "main")
        show_structure: Whether to print the repository structure after importing
        
    Returns:
        A module object representing the repository.
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
    with tqdm(total=100, desc="Building module", ascii=True) as pbar:
        # Parse repo name from path for the module name
        if "/" in repo_path:
            repo_name = repo_path.split("/")[-1]
        else:
            repo_name = repo_path
        
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        
        pbar.update(20)  # Update progress
        
        # Add the repository directory to sys.path temporarily
        parent_dir = os.path.dirname(local_path)
        sys.path.insert(0, parent_dir)
        
        try:
            # Import the repository as a module
            pbar.update(40)  # Update progress
            module = _create_module(repo_name, local_path)
            pbar.update(40)  # Update progress to 100%
            
            # Store in cache
            _REPO_CACHE[cache_key] = module
            _REPO_PATHS[cache_key] = local_path
            
            if show_structure:
                print("\n📂 Repository structure:")
                print(get_structure(local_path))
            
            return module
        finally:
            # Remove the directory from sys.path
            if parent_dir in sys.path:
                sys.path.remove(parent_dir)

def update_repo(repo_path: str, branch: str = "main", show_structure: bool = True) -> types.ModuleType:
    """
    Update a previously imported GitHub repository.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        branch: The branch to update (default: "main")
        show_structure: Whether to print the repository structure after updating
        
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

def get_repo_structure(repo_name: str) -> str:
    """
    Get the structure of an imported repository.
    
    Args:
        repo_name: The name of the repository or the full path (username/repo_name)
        
    Returns:
        A formatted string showing the repository structure
    """
    # Find the repository in _REPO_PATHS
    repo_short_name = repo_name.split("/")[-1]
    if repo_short_name.endswith(".git"):
        repo_short_name = repo_short_name[:-4]
    
    # Search for the repository in _REPO_PATHS
    for cache_key, path in _REPO_PATHS.items():
        if repo_short_name in cache_key:
            return get_structure(path)
    
    # If not found, try to find it in the temporary directory
    local_path = _get_local_path(repo_short_name)
    if os.path.exists(local_path):
        return get_structure(local_path)
    
    return f"Repository {repo_name} not found in cache or local directory"


def dynamic_import(repo_path: str, module_path: Optional[str] = None) -> types.ModuleType:
    """
    Dynamically import modules from a repository path.
    
    Args:
        repo_path: Path to the repository directory
        module_path: Specific module path within the repository
        
    Returns:
        The imported module or package
    """
    repo_name = os.path.basename(repo_path)
    if module_path:
        module_name = f"{repo_name}.{module_path}"
        module_full_path = os.path.join(repo_path, module_path.replace(".", os.path.sep))
    else:
        module_name = repo_name
        module_full_path = repo_path
    
    return _create_module(module_name, module_full_path)

def import_specific_module(repo_path: str, module_path: str, branch: str = "main") -> types.ModuleType:
    """
    Import a specific module from a GitHub repository.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        module_path: Path to the specific module within the repository (e.g. 'utils/helpers')
        branch: The branch to import (default: "main")
        
    Returns:
        The imported module
    """
    # First import the entire repository
    repo_module = import_repo(repo_path, branch, show_structure=False)
    
    # Get the local path of the repository
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    local_path = _get_local_path(repo_name)
    
    # Calculate the full path to the specific module
    full_module_path = os.path.join(local_path, module_path.replace(".", "/"))
    if os.path.isdir(full_module_path):
        # It's a directory, make sure we have the right path format
        if not full_module_path.endswith("/"):
            full_module_path += "/"
        full_module_path += "__init__.py"
    elif not full_module_path.endswith(".py"):
        # Add .py extension if not present
        full_module_path += ".py"
    
    if not os.path.exists(full_module_path):
        raise ImportError(f"Module '{module_path}' not found in repository {repo_path}")
    
    # Import the specific module
    module_name = f"{repo_name}.{module_path.replace('/', '.')}"
    return import_module_from_path(module_name, full_module_path)