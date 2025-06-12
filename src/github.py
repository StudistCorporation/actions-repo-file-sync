"""GitHub API client for downloading repository files.

This module provides functionality to download files from GitHub repositories
using the raw content API endpoint.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub repositories.

    Provides methods to download files from public and private GitHub repositories.
    Uses raw.githubusercontent.com for public repos and GitHub API for private repos.
    """

    BASE_URL = "https://raw.githubusercontent.com"
    API_URL = "https://api.github.com"

    def __init__(self, timeout: int = 30, token: Optional[str] = None):
        """Initialize the GitHub client.

        Args:
            timeout: Request timeout in seconds
            token: Optional GitHub token for private repository access
        """
        self.timeout = timeout
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        
        # Set user agent for proper API usage
        self.session.headers.update({"User-Agent": "actions-repo-file-sync/2.0.0"})
        
        # Add authorization header if token is available
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
            logger.debug("GitHub token configured for private repository access")

    def download_file(
        self,
        repo: str,
        ref: str,
        file_path: str,
        output_path: Optional[Path] = None,
        env_vars: Optional[dict[str, str]] = None,
    ) -> bytes:
        """Download a file from a GitHub repository.

        Downloads the specified file from the given repository and git reference.
        Optionally saves the content to a local file.

        Args:
            repo: Repository in format 'owner/repo'
            ref: Git reference (branch, tag, or commit hash)
            file_path: Path to the file within the repository
            output_path: Optional local path to save the file
            env_vars: Optional environment variables for content substitution

        Returns:
            File content as bytes (after environment variable substitution)

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
        logger.info(f"Downloading {repo}:{ref}:{file_path}")
        
        # Try raw.githubusercontent.com first (works for public repos and private with token)
        content = self._download_via_raw_url(repo, ref, file_path)
        
        # If raw URL fails and we have a token, try GitHub API
        if content is None and self.token:
            logger.debug("Raw URL failed, trying GitHub API")
            content = self._download_via_api(repo, ref, file_path)
        
        if content is None:
            raise FileNotFoundError(f"File not found: {repo}:{ref}:{file_path}")

        logger.info(
            f"Successfully downloaded {repo}:{ref}:{file_path} ({len(content)} bytes)"
        )

        # Perform environment variable substitution if specified
        if env_vars:
            content = self._substitute_env_vars(content, env_vars)
            logger.debug(
                f"Applied environment variable substitution to {repo}:{ref}:{file_path}"
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

    def _download_via_raw_url(self, repo: str, ref: str, file_path: str) -> Optional[bytes]:
        """Download file using raw.githubusercontent.com endpoint.
        
        Args:
            repo: Repository in format 'owner/repo'
            ref: Git reference
            file_path: Path to file in repository
            
        Returns:
            File content as bytes, or None if download fails
        """
        try:
            # URL encode the file path to handle spaces and special characters
            encoded_file_path = quote(file_path, safe="/")
            url = f"{self.BASE_URL}/{repo}/{ref}/{encoded_file_path}"
            
            logger.debug(f"Trying raw URL: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Raw URL download failed: {e}")
            return None

    def _download_via_api(self, repo: str, ref: str, file_path: str) -> Optional[bytes]:
        """Download file using GitHub API endpoint.
        
        Args:
            repo: Repository in format 'owner/repo'
            ref: Git reference
            file_path: Path to file in repository
            
        Returns:
            File content as bytes, or None if download fails
        """
        try:
            # URL encode the file path to handle spaces and special characters
            encoded_file_path = quote(file_path, safe="/")
            url = f"{self.API_URL}/repos/{repo}/contents/{encoded_file_path}"
            
            params = {"ref": ref}
            logger.debug(f"Trying API URL: {url} with ref={ref}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # GitHub API returns base64-encoded content
            if data.get("encoding") == "base64":
                content = base64.b64decode(data["content"])
                return content
            else:
                logger.error(f"Unexpected encoding: {data.get('encoding')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"API download failed: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"API response parsing failed: {e}")
            return None

    def _substitute_env_vars(self, content: bytes, env_vars: dict[str, str]) -> bytes:
        """Substitute environment variables in file content.

        Replaces occurrences of environment variable names with their values
        in the file content. Only substitutes if the file appears to be text.

        Args:
            content: Original file content as bytes
            env_vars: Dictionary mapping variable names to values

        Returns:
            Modified content with environment variables substituted
        """
        try:
            # Try to decode as text - if it fails, return original content
            text_content = content.decode("utf-8")

            # Perform substitutions
            modified_content = text_content
            substitutions_made = 0

            for name, value in env_vars.items():
                if name in modified_content:
                    old_content = modified_content
                    modified_content = modified_content.replace(name, value)
                    if modified_content != old_content:
                        substitutions_made += 1
                        logger.debug(f"Replaced '{name}' with '{value}'")

            if substitutions_made > 0:
                logger.info(
                    f"Made {substitutions_made} environment variable substitutions"
                )

            return modified_content.encode("utf-8")

        except UnicodeDecodeError:
            # File is binary, return original content unchanged
            logger.debug(
                "File appears to be binary, skipping environment variable substitution"
            )
            return content

    def test_connection(self) -> bool:
        """Test connection to GitHub by making a simple request.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Test with a known public file
            response = self.session.get(
                f"{self.BASE_URL}/actions/checkout/main/README.md", timeout=self.timeout
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
