"""GitHub API client for downloading repository files.

This module provides functionality to download files from GitHub repositories
using the raw content API endpoint.
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
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

    def _download_via_raw_url(
        self, repo: str, ref: str, file_path: str
    ) -> Optional[bytes]:
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

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> Optional[str]:
        """Create a pull request in the specified repository.

        Args:
            repo: Repository in format 'owner/repo'
            title: Title of the pull request
            body: Body/description of the pull request
            head_branch: Source branch name
            base_branch: Target branch name (default: 'main')

        Returns:
            Pull request URL if successful, None otherwise

        Example:
            >>> client = GitHubClient()
            >>> pr_url = client.create_pull_request(
            ...     "owner/repo",
            ...     "🔄 Sync files from repositories",
            ...     "Automated file sync",
            ...     "sync/repo-files"
            ... )
            >>> print(pr_url)
            'https://github.com/owner/repo/pull/123'
        """
        if not self.token:
            logger.error("GitHub token required for creating pull requests")
            return None

        try:
            url = f"{self.API_URL}/repos/{repo}/pulls"
            data = {
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
            }

            logger.info(f"Creating pull request: {title}")
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()

            pr_data = response.json()
            pr_url = pr_data["html_url"]
            pr_number = pr_data["number"]

            logger.info(f"Pull request created successfully: #{pr_number}")
            return pr_url

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse pull request response: {e}")
            return None

    def setup_git_and_push(
        self,
        branch_name: str,
        commit_message: str,
        files_to_add: list[str],
    ) -> bool:
        """Set up git configuration and push changes to a new branch.

        Args:
            branch_name: Name of the branch to create and push to
            commit_message: Commit message for the changes
            files_to_add: List of file paths to add to the commit

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Setting up git and pushing branch: {branch_name}")
            
            # Change to GitHub workspace directory (where the git repository is)
            import os
            workspace_dir = os.getenv("GITHUB_WORKSPACE", "/github/workspace")
            original_cwd = os.getcwd()
            logger.debug(f"Changing directory from {original_cwd} to {workspace_dir}")
            
            # Debug: Check directory contents and git status
            logger.debug(f"Current directory contents: {os.listdir('.')}")
            if os.path.exists(workspace_dir):
                logger.debug(f"Workspace directory contents: {os.listdir(workspace_dir)}")
                os.chdir(workspace_dir)
                logger.debug(f"After chdir, current directory: {os.getcwd()}")
                logger.debug(f"Directory contents: {os.listdir('.')}")
                
                # Check if .git exists
                if os.path.exists(".git"):
                    logger.debug(".git directory exists")
                else:
                    logger.error(".git directory does NOT exist")
                    
                # Try to get git status for debugging
                try:
                    result = subprocess.run(["git", "status"], capture_output=True, text=True)
                    logger.debug(f"Git status result: {result.returncode}")
                    if result.stdout:
                        logger.debug(f"Git status stdout: {result.stdout}")
                    if result.stderr:
                        logger.debug(f"Git status stderr: {result.stderr}")
                except Exception as e:
                    logger.debug(f"Git status failed: {e}")
            else:
                logger.error(f"Workspace directory {workspace_dir} does not exist")
                return False
            
            # Configure git safe directory first
            logger.debug("Adding git safe directory")
            subprocess.run(
                ["git", "config", "--global", "--add", "safe.directory", workspace_dir],
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Configure git user
            logger.debug("Configuring git user")
            subprocess.run(
                ["git", "config", "user.name", "actions-repo-file-sync"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "action@github.com"],
                check=True,
                capture_output=True,
                text=True,
            )

            # Check current status
            logger.debug("Checking git status")
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            )
            
            if not status_result.stdout.strip():
                logger.info("No changes detected, skipping commit and PR creation")
                return False

            # Create and checkout new branch (delete if exists)
            logger.debug(f"Creating branch: {branch_name}")
            try:
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    capture_output=True,
                    text=True,
                )
                logger.debug(f"Deleted existing branch: {branch_name}")
            except subprocess.CalledProcessError:
                pass  # Branch doesn't exist, that's fine

            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                check=True,
                capture_output=True,
                text=True,
            )

            # Add files
            logger.debug(f"Adding files: {files_to_add}")
            for file_path in files_to_add:
                result = subprocess.run(
                    ["git", "add", file_path],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    logger.warning(f"Failed to add {file_path}: {result.stderr}")

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "diff", "--staged", "--quiet"],
                capture_output=True,
            )

            if result.returncode == 0:
                logger.info("No staged changes to commit")
                return False

            # Show what will be committed
            diff_result = subprocess.run(
                ["git", "diff", "--staged", "--name-only"],
                capture_output=True,
                text=True,
            )
            logger.info(f"Files to be committed: {diff_result.stdout.strip()}")

            # Commit changes
            logger.debug("Committing changes")
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True,
                text=True,
            )

            # Push to remote
            logger.debug(f"Pushing branch: {branch_name}")
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(f"Successfully pushed branch: {branch_name}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            if e.stderr:
                logger.error(f"Git stderr: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
            if e.stdout:
                logger.debug(f"Git stdout: {e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout}")
            return False
        finally:
            # Restore original working directory
            try:
                os.chdir(original_cwd)
                logger.debug(f"Restored working directory to {original_cwd}")
            except:
                pass  # Don't fail if we can't restore directory
