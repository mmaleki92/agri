"""
Authentication utilities for GitHub access.
"""
import os
import getpass
import warnings
from typing import Optional

# Service name for keyring
SERVICE_NAME = "agri"
ACCOUNT_NAME = "github_token"

# In-memory fallback token storage when keyring fails
_MEMORY_TOKEN = None

def authenticate(token: Optional[str] = None, store: bool = True) -> str:
    """
    Authenticate with GitHub using a personal access token.
    
    Args:
        token: The GitHub personal access token. If None, will try to retrieve
               from keyring or environment variables, or prompt the user.
        store: Whether to store the token for future use.
        
    Returns:
        The authenticated token.
    """
    global _MEMORY_TOKEN
    
    # Try to get token if not provided
    if token is None:
        # Try environment variable first (always works)
        token = os.environ.get("GITHUB_TOKEN")
        
        # Try memory cache next (works within session)
        if token is None and _MEMORY_TOKEN is not None:
            token = _MEMORY_TOKEN
            
        # Try to get from keyring (might fail in some environments)
        if token is None:
            try:
                import keyring
                token = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
            except Exception as e:
                # Keyring access failed, but we can continue
                pass
        
        # Prompt user if still not found
        if token is None:
            token = getpass.getpass("Enter your GitHub Personal Access Token: ")
    
    if not token:
        raise ValueError("GitHub token is required for authentication")
    
    # Store token for future use if requested
    if store:
        # Always set in environment (session only)
        os.environ["GITHUB_TOKEN"] = token
        
        # Always store in memory (session only)
        _MEMORY_TOKEN = token
        
        # Try to store in keyring (persistent)
        try:
            import keyring
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, token)
        except Exception as e:
            warnings.warn(
                f"Could not store token in keyring: {str(e)}\n"
                "Your token will only be available for the current session.\n"
                "Consider installing a keyring backend: pip install keyrings.alt"
            )
            
    return token

def get_token() -> str:
    """
    Get the currently authenticated token.
    
    Returns:
        The current GitHub token or raises an error if not authenticated.
    """
    # Check environment first
    token = os.environ.get("GITHUB_TOKEN")
    
    # Check memory cache next
    if token is None and _MEMORY_TOKEN is not None:
        token = _MEMORY_TOKEN
        
    # Try keyring last (might fail in some environments)
    if token is None:
        try:
            import keyring
            token = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception:
            # Keyring access failed, but we might still have a token elsewhere
            pass
    
    if not token:
        raise RuntimeError(
            "Not authenticated. Call authenticate() first with your GitHub token."
        )
        
    return token