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


def commit_files(repo_path: str, 
                local_source: Union[str, Dict[str, str]], 
                repo_target: str = "", 
                message: str = "Update files", 
                branch: str = "main", 
                push: bool = True) -> bool:
    """
    Commit local files or folders to a repository.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        local_source: Path to local file/folder, or dict mapping local paths to repository paths
        repo_target: Target path within the repository (default: root of repository)
                    (only used if local_source is a string)
        message: Commit message
        branch: Branch to commit to
        push: Whether to push changes to remote repository
        
    Returns:
        True if successful, False otherwise
    """
    # Parse repo name from path
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    local_repo_path = _get_local_path(repo_name)
    
    # Check if repository exists locally
    if not os.path.exists(local_repo_path):
        print(f"⚠️ Repository {repo_path} not found locally. Cloning fresh copy...")
        _clone_repo(repo_path, branch)
    
    try:
        # Open the repository
        repo = git.Repo(local_repo_path)
        
        # Update remote URL with token
        auth_url = _get_repo_url(repo_path)
        origin = repo.remote(name="origin")
        origin.set_url(auth_url)
        
        # Ensure we're on the right branch
        current_branch = repo.active_branch.name
        if current_branch != branch:
            print(f"🔄 Switching from branch '{current_branch}' to '{branch}'")
            try:
                repo.git.checkout(branch)
            except git.exc.GitCommandError:
                # Branch doesn't exist locally, try to find it on remote
                try:
                    print(f"🔍 Branch '{branch}' not found locally, checking remote...")
                    repo.git.fetch('origin', branch)
                    repo.git.checkout('-b', branch, f'origin/{branch}')
                except git.exc.GitCommandError:
                    # Branch doesn't exist remotely either, create it
                    print(f"🌱 Creating new branch '{branch}'")
                    repo.git.checkout('-b', branch)
        
        # Pull latest changes
        try:
            print(f"⬇️ Pulling latest changes from origin/{branch}...")
            repo.git.pull('origin', branch)
        except git.exc.GitCommandError as e:
            if "no tracking information" in str(e):
                print(f"⚠️ Branch '{branch}' has no tracking information. Skipping pull.")
            else:
                raise
        
        # Process file copying
        print(f"📝 Copying files to repository...")
        files_copied = False
        
        # Handle different input types
        if isinstance(local_source, str):
            # Single source path with target directory
            files_copied = _copy_to_repo(local_source, local_repo_path, repo_target)
        elif isinstance(local_source, dict):
            # Multiple source paths with individual target paths
            for src, dst in local_source.items():
                if _copy_to_repo(src, local_repo_path, dst):
                    files_copied = True
        else:
            raise ValueError("local_source must be either a string path or a dict mapping source to target paths")
        
        if not files_copied:
            print("ℹ️ No files were copied")
            return False
            
        # Stage all changes
        repo.git.add('--all')
        
        # Check if there are changes to commit
        if not repo.is_dirty() and len(repo.index.diff("HEAD")) == 0:
            print("ℹ️ No changes to commit")
            return False
        
        # Commit changes
        print(f"💾 Committing changes to {branch} branch...")
        repo.git.commit('-m', message)
        
        if push:
            # Push to remote
            print(f"🚀 Pushing changes to remote repository...")
            repo.git.push('--set-upstream', 'origin', branch)
            print(f"✅ Changes pushed successfully")
        
        return True
        
    except git.exc.GitCommandError as e:
        print(f"❌ Error committing changes: {e}")
        return False

def _copy_to_repo(source_path: str, repo_path: str, repo_target: str) -> bool:
    """
    Helper function to copy files or directories to the repository.
    
    Args:
        source_path: Local file or directory path
        repo_path: Local path to the repository
        repo_target: Target path within the repository
        
    Returns:
        True if files were copied, False otherwise
    """
    # Calculate full target path in the repository
    target_path = os.path.join(repo_path, repo_target.lstrip('/'))
    
    # Make sure target directory exists
    if os.path.isfile(source_path):
        os.makedirs(os.path.dirname(target_path) if repo_target else target_path, exist_ok=True)
    else:
        os.makedirs(target_path, exist_ok=True)
    
    try:
        # Handle different source types
        if os.path.isfile(source_path):
            # It's a file
            if os.path.isdir(target_path):
                # Target is a directory, put file inside it
                dest = os.path.join(target_path, os.path.basename(source_path))
            else:
                # Target is a file path
                dest = target_path
                
            shutil.copy2(source_path, dest)
            print(f"📄 Copied {source_path} -> {dest}")
            return True
            
        elif os.path.isdir(source_path):
            # It's a directory, copy all contents
            items_copied = 0
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(target_path, item)
                
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                    print(f"📁 Copied directory {s} -> {d}")
                else:
                    shutil.copy2(s, d)
                    print(f"📄 Copied {s} -> {d}")
                items_copied += 1
                
            return items_copied > 0
        else:
            print(f"⚠️ Source path {source_path} does not exist")
            return False
            
    except Exception as e:
        print(f"❌ Error copying files: {e}")
        return False

def create_file_and_commit(repo_path: str, 
                          file_content: str,
                          repo_file_path: str,
                          message: str = "Add or update file",
                          branch: str = "main",
                          push: bool = True) -> bool:
    """
    Create or update a file with specified content and commit it to the repository.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        file_content: Content to write to the file
        repo_file_path: Path to the file within the repository
        message: Commit message
        branch: Branch to commit to
        push: Whether to push changes to remote repository
        
    Returns:
        True if successful, False otherwise
    """
    # Parse repo name from path
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    local_repo_path = _get_local_path(repo_name)
    
    # Check if repository exists locally
    if not os.path.exists(local_repo_path):
        print(f"⚠️ Repository {repo_path} not found locally. Cloning fresh copy...")
        _clone_repo(repo_path, branch)
    
    try:
        # Open the repository
        repo = git.Repo(local_repo_path)
        
        # Update remote URL with token
        auth_url = _get_repo_url(repo_path)
        origin = repo.remote(name="origin")
        origin.set_url(auth_url)
        
        # Ensure we're on the right branch
        current_branch = repo.active_branch.name
        if current_branch != branch:
            print(f"🔄 Switching from branch '{current_branch}' to '{branch}'")
            try:
                repo.git.checkout(branch)
            except git.exc.GitCommandError:
                # Branch doesn't exist locally, try to find it on remote
                try:
                    print(f"🔍 Branch '{branch}' not found locally, checking remote...")
                    repo.git.fetch('origin', branch)
                    repo.git.checkout('-b', branch, f'origin/{branch}')
                except git.exc.GitCommandError:
                    # Branch doesn't exist remotely either, create it
                    print(f"🌱 Creating new branch '{branch}'")
                    repo.git.checkout('-b', branch)
        
        # Pull latest changes
        try:
            print(f"⬇️ Pulling latest changes from origin/{branch}...")
            repo.git.pull('origin', branch)
        except git.exc.GitCommandError as e:
            if "no tracking information" in str(e):
                print(f"⚠️ Branch '{branch}' has no tracking information. Skipping pull.")
            else:
                raise
        
        # Create or update the file
        file_path = os.path.join(local_repo_path, repo_file_path.lstrip('/'))
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
            
        print(f"✏️ Created/updated file: {repo_file_path}")
        
        # Stage the file
        repo.git.add(file_path)
        
        # Check if there are changes to commit
        if not repo.is_dirty() and len(repo.index.diff("HEAD")) == 0:
            print("ℹ️ No changes to commit")
            return False
        
        # Commit changes
        print(f"💾 Committing changes to {branch} branch...")
        repo.git.commit('-m', message)
        
        if push:
            # Push to remote
            print(f"🚀 Pushing changes to remote repository...")
            repo.git.push('--set-upstream', 'origin', branch)
            print(f"✅ Changes pushed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating and committing file: {e}")
        return False

def delete_files_and_commit(repo_path: str, 
                          repo_file_paths: Union[str, List[str]],
                          message: str = "Delete files",
                          branch: str = "main",
                          push: bool = True) -> bool:
    """
    Delete files or directories from the repository and commit the changes.
    
    Args:
        repo_path: The path to the repository (username/repo_name)
        repo_file_paths: Path(s) to the file(s) or directory(ies) to delete within the repository
        message: Commit message
        branch: Branch to commit to
        push: Whether to push changes to remote repository
        
    Returns:
        True if successful, False otherwise
    """
    # Convert single path to list
    if isinstance(repo_file_paths, str):
        repo_file_paths = [repo_file_paths]
        
    # Parse repo name from path
    if "/" in repo_path:
        repo_name = repo_path.split("/")[-1]
    else:
        repo_name = repo_path
    
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    local_repo_path = _get_local_path(repo_name)
    
    # Check if repository exists locally
    if not os.path.exists(local_repo_path):
        print(f"⚠️ Repository {repo_path} not found locally. Cloning fresh copy...")
        _clone_repo(repo_path, branch)
    
    try:
        # Open the repository
        repo = git.Repo(local_repo_path)
        
        # Update remote URL with token
        auth_url = _get_repo_url(repo_path)
        origin = repo.remote(name="origin")
        origin.set_url(auth_url)
        
        # Handle branch switching and pulling as in other methods
        current_branch = repo.active_branch.name
        if current_branch != branch:
            print(f"🔄 Switching from branch '{current_branch}' to '{branch}'")
            try:
                repo.git.checkout(branch)
            except git.exc.GitCommandError:
                try:
                    repo.git.fetch('origin', branch)
                    repo.git.checkout('-b', branch, f'origin/{branch}')
                except git.exc.GitCommandError:
                    print(f"🌱 Creating new branch '{branch}'")
                    repo.git.checkout('-b', branch)
        
        try:
            print(f"⬇️ Pulling latest changes from origin/{branch}...")
            repo.git.pull('origin', branch)
        except git.exc.GitCommandError as e:
            if "no tracking information" in str(e):
                print(f"⚠️ Branch '{branch}' has no tracking information. Skipping pull.")
            else:
                raise
        
        # Delete files
        files_deleted = False
        for path in repo_file_paths:
            full_path = os.path.join(local_repo_path, path.lstrip('/'))
            if os.path.exists(full_path):
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                    print(f"🗑️ Deleted directory: {path}")
                else:
                    os.remove(full_path)
                    print(f"🗑️ Deleted file: {path}")
                files_deleted = True
            else:
                print(f"⚠️ Path not found: {path}")
        
        if not files_deleted:
            print("ℹ️ No files were deleted")
            return False
        
        # Stage deletions
        repo.git.add('--all')
        
        # Commit changes
        print(f"💾 Committing changes to {branch} branch...")
        repo.git.commit('-m', message)
        
        if push:
            # Push to remote
            print(f"🚀 Pushing changes to remote repository...")
            repo.git.push('--set-upstream', 'origin', branch)
            print(f"✅ Changes pushed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting files and committing: {e}")
        return False
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
def get_repo_structure(repo_name: Union[str, LazyModule], ignore_patterns: List[str] = None) -> str:
    """
    Get the structure of an imported repository.
    
    Args:
        repo_name: The name of the repository (string) or a LazyModule object
        ignore_patterns: List of patterns to ignore (e.g. [".git", "__pycache__"])
        
    Returns:
        A formatted string showing the directory structure
    """
    if ignore_patterns is None:
        ignore_patterns = [".git", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", 
                           "venv", "env", ".env", ".github", ".vscode"]
    
    # Check if repo_name is a LazyModule object
    if hasattr(repo_name, '__class__') and repo_name.__class__.__name__ == 'LazyModule':
        # It's a LazyModule object, get structure directly from its path
        module_path = repo_name.__path__

        print("📂 Repository structure:")
        return get_structure(module_path, ignore_patterns=ignore_patterns)
    
    # It's a string, process as before
    if isinstance(repo_name, str):
        # Extract the short name from the full path if needed
        if "/" in repo_name:
            repo_short_name = repo_name.split("/")[-1]
        else:
            repo_short_name = repo_name
            
        if repo_short_name.endswith(".git"):
            repo_short_name = repo_short_name[:-4]
        
        # Try finding by direct name match first
        for cache_key, path in _REPO_PATHS.items():
            if f"{repo_name}:" in cache_key or f"/{repo_short_name}:" in cache_key:
                print(f"📂 Repository structure for {repo_name}:")
                return get_structure(path, ignore_patterns=ignore_patterns)
        
        # If not found by direct match, try partial match
        for cache_key, path in _REPO_PATHS.items():
            if repo_short_name in cache_key:
                print(f"📂 Repository structure for {repo_name}:")
                return get_structure(path, ignore_patterns=ignore_patterns)
        
        # If not found in cache, try to find it in the temporary directory
        local_path = _get_local_path(repo_short_name)
        if os.path.exists(local_path):
            print(f"📂 Repository structure for {repo_name} (from local path):")
            return get_structure(local_path, ignore_patterns=ignore_patterns)
            
    return "⚠️ Repository not found in cache or local directory"


def list_imported_repos() -> List[str]:
    """
    List all imported repositories in the cache.
    
    Returns:
        A list of repository names that have been imported.
    """
    repos = []
    for cache_key in _REPO_CACHE.keys():
        # cache_key is in format "owner/repo:branch"
        repo_info = cache_key.split(':')
        if len(repo_info) >= 2:
            repo_path = repo_info[0]
            branch = repo_info[1]
            repos.append(f"{repo_path} (branch: {branch})")
        else:
            repos.append(cache_key)
    
    return repos