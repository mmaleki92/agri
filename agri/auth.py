"""
Authentication utilities for GitHub repositories.
"""
import os
import getpass
import keyring
from typing import Optional

# Service name for keyring
SERVICE_NAME = "agri"
ACCOUNT_NAME = "github_token"

def authenticate(token: Optional[str] = None, store: bool = True) -> str:
    """
    Authenticate with GitHub using a personal access token.
    
    Args:
        token: The GitHub personal access token. If None, will try to retrieve
               from keyring or environment variables, or prompt the user.
        store: Whether to store the token in the keyring for future use.
        
    Returns:
        The authenticated token.
    """
    # Try to get token if not provided
    if token is None:
        # Try to get from keyring
        token = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        
        # Try to get from environment variables
        if token is None:
            token = os.environ.get("GITHUB_TOKEN")
        
        # Prompt user if still not found
        if token is None:
            token = getpass.getpass("Enter your GitHub Personal Access Token: ")
    
    if not token:
        raise ValueError("GitHub token is required for authentication")
        
    # Store token for future use if requested
    if store:
        keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, token)
        # Also set as environment variable for current session
        os.environ["GITHUB_TOKEN"] = token
        
    return token

def get_token() -> str:
    """
    Get the currently authenticated token.
    
    Returns:
        The current GitHub token or raises an error if not authenticated.
    """
    token = os.environ.get("GITHUB_TOKEN") or keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    
    if not token:
        raise RuntimeError(
            "Not authenticated. Call authenticate() first with your GitHub token."
        )
        
    return token