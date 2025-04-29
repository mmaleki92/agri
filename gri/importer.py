"""
Dynamic import utilities for GitHub repositories.
"""
import sys
import os
import importlib.util
import types

def import_module_from_path(module_name, module_path):
    """Import a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:
        raise ImportError(f"Could not find module {module_name} at {module_path}")
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def dynamic_import(repo_path, module_path=None):
    """
    Dynamically import modules from a repository path.
    
    Args:
        repo_path: Path to the repository directory
        module_path: Specific module path within the repository
        
    Returns:
        The imported module or package
    """
    # This functionality is now in repo_manager.py
    from .repo_manager import _create_module
    
    repo_name = os.path.basename(repo_path)
    if module_path:
        module_name = f"{repo_name}.{module_path}"
        module_full_path = os.path.join(repo_path, module_path.replace(".", os.path.sep))
    else:
        module_name = repo_name
        module_full_path = repo_path
    
    return _create_module(module_name, module_full_path)