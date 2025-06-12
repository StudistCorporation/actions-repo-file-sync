"""GitHub API client for downloading repository files.

This module provides functionality to download files from GitHub repositories
using the raw content API endpoint.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub repositories.
    
    Provides methods to download files from public GitHub repositories
    using the raw.githubusercontent.com endpoint.
    """
    
    BASE_URL = "https://raw.githubusercontent.com"
    
    def __init__(self, timeout: int = 30):
        """Initialize the GitHub client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        # Set user agent for proper API usage
        self.session.headers.update({
            "User-Agent": "actions-repo-file-sync/2.0.0"
        })
    
    def download_file(
        self,
        repo: str,
        ref: str,
        file_path: str,
        output_path: Optional[Path] = None,
    ) -> bytes:
        """Download a file from a GitHub repository.
        
        Downloads the specified file from the given repository and git reference.
        Optionally saves the content to a local file.
        
        Args:
            repo: Repository in format 'owner/repo'
            ref: Git reference (branch, tag, or commit hash)
            file_path: Path to the file within the repository
            output_path: Optional local path to save the file
            
        Returns:
            File content as bytes
            
        Raises:
            requests.RequestException: If the download fails
            FileNotFoundError: If the file doesn't exist in the repository
            
        Example:
            >>> client = GitHubClient()
            >>> content = client.download_file(
            ...     "actions/checkout",
            ...     "main", 
            ...     "README.md"
            ... )
            >>> print(len(content))
            5432
        """
        # URL encode the file path to handle spaces and special characters
        encoded_file_path = quote(file_path, safe="/")
        url = f"{self.BASE_URL}/{repo}/{ref}/{encoded_file_path}"
        
        logger.info(f"Downloading {repo}:{ref}:{file_path}")
        logger.debug(f"Request URL: {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise FileNotFoundError(
                    f"File not found: {repo}:{ref}:{file_path}"
                ) from e
            raise requests.RequestException(
                f"Failed to download {repo}:{ref}:{file_path}: {e}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(
                f"Network error downloading {repo}:{ref}:{file_path}: {e}"
            ) from e
        
        content = response.content
        logger.info(
            f"Successfully downloaded {repo}:{ref}:{file_path} "
            f"({len(content)} bytes)"
        )
        
        # Save to file if output path specified
        if output_path:
            self._save_file(content, output_path)
        
        return content
    
    def _save_file(self, content: bytes, output_path: Path) -> None:
        """Save content to a local file.
        
        Creates parent directories if they don't exist and writes
        the content to the specified path.
        
        Args:
            content: File content to save
            output_path: Local path to save the file
            
        Raises:
            OSError: If file creation fails
        """
        try:
            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with output_path.open("wb") as f:
                f.write(content)
            
            logger.info(f"Saved file to {output_path}")
        except OSError as e:
            logger.error(f"Failed to save file to {output_path}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to GitHub by making a simple request.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Test with a known public file
            response = self.session.get(
                f"{self.BASE_URL}/actions/checkout/main/README.md",
                timeout=self.timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def close(self) -> None:
        """Close the HTTP session.
        
        Should be called when done using the client to clean up resources.
        """
        self.session.close()
    
    def __enter__(self) -> GitHubClient:
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()