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
        reviewers: Optional[list[str]] = None,
        team_reviewers: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Create a pull request in the specified repository, based on TypeScript implementation.

        Args:
            repo: Repository in format 'owner/repo'
            title: Title of the pull request
            body: Body/description of the pull request
            head_branch: Source branch name
            base_branch: Target branch name (default: 'main')
            reviewers: List of user reviewers to request
            team_reviewers: List of team reviewers to request

        Returns:
            Pull request URL if successful, None otherwise

        Example:
            >>> client = GitHubClient()
            >>> pr_url = client.create_pull_request(
            ...     "owner/repo",
            ...     "[repo-file-sync] Synchronize files",
            ...     "Automated file sync",
            ...     "sync/repo-files",
            ...     reviewers=["user1", "user2"]
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

            # Add reviewers if specified (like TypeScript version)
            if reviewers or team_reviewers:
                self._add_pr_reviewers(repo, pr_number, reviewers, team_reviewers)

            return pr_url

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse pull request response: {e}")
            return None

    def _add_pr_reviewers(
        self,
        repo: str,
        pr_number: int,
        reviewers: Optional[list[str]] = None,
        team_reviewers: Optional[list[str]] = None,
    ) -> bool:
        """Add reviewers to a pull request.

        Args:
            repo: Repository in format 'owner/repo'
            pr_number: Pull request number
            reviewers: List of user reviewers to add
            team_reviewers: List of team reviewers to add

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.API_URL}/repos/{repo}/pulls/{pr_number}/requested_reviewers"
            data = {}
            
            if reviewers:
                data["reviewers"] = reviewers
            if team_reviewers:
                data["team_reviewers"] = team_reviewers
            
            if not data:
                return True  # Nothing to add
            
            logger.info(f"Adding reviewers to PR #{pr_number}: {data}")
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            logger.info(f"Successfully added reviewers to PR #{pr_number}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add reviewers to PR #{pr_number}: {e}")
            return False

    def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """Create and checkout a git branch, based on TypeScript implementation.

        Args:
            branch_name: Name of the branch to create
            base_branch: Base branch to create from (default: main)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Configure git user
            subprocess.run(
                ["git", "config", "user.name", "actions-repo-file-sync"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "action@github.com"],
                check=True,
                capture_output=True,
            )

            # Try to fetch existing branch first (like TypeScript version)
            try:
                logger.info(f"Attempting to fetch and checkout existing branch: {branch_name}")
                subprocess.run(
                    ["git", "fetch", "origin", branch_name],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
                    check=True,
                    capture_output=True,
                )
                logger.info(f"Successfully checked out existing branch: {branch_name}")
            except subprocess.CalledProcessError:
                # Branch doesn't exist, create new one from base branch
                logger.info(f"Creating new branch {branch_name} from {base_branch}")
                subprocess.run(
                    ["git", "checkout", "-b", branch_name, base_branch],
                    check=True,
                    capture_output=True,
                )
                logger.info(f"Successfully created new branch: {branch_name}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create/checkout branch {branch_name}: {e}")
            return False

    def add_files_and_push(
        self,
        branch_name: str,
        commit_message: str = "[repo-file-sync] Synchronize files",
        files_to_add: Optional[list[str]] = None,
    ) -> bool:
        """Add files to git and push to remote branch, based on TypeScript implementation.

        Args:
            branch_name: Name of the branch to push to
            commit_message: Commit message for the changes
            files_to_add: List of file paths to add, or None to add all changes

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add files based on TypeScript pattern: add -N . first, then check diff
            if files_to_add:
                # Add specific files
                for file_path in files_to_add:
                    subprocess.run(
                        ["git", "add", file_path],
                        check=True,
                        capture_output=True,
                    )
            else:
                # Add all files (TypeScript pattern: git add -N .)
                subprocess.run(
                    ["git", "add", "-N", "."],
                    check=True,
                    capture_output=True,
                )

            # Check if there are changes using git diff --name-only (like TypeScript)
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
            )

            changed_files = result.stdout.strip()
            if not changed_files:
                logger.info("No changes detected to commit")
                return True  # Return True to allow PR creation workflow to continue
            
            logger.info(f"Changes detected in files: {changed_files}")
            
            # Add all changes and commit (like TypeScript: git add .)
            subprocess.run(
                ["git", "add", "."],
                check=True,
                capture_output=True,
            )

            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True,
            )

            # Push to remote
            subprocess.run(
                ["git", "push", "origin", branch_name],
                check=True,
                capture_output=True,
            )

            logger.info(f"Successfully pushed changes to branch: {branch_name}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to add files and push to {branch_name}: {e}")
            return False

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
        # Create branch
        if not self.create_branch(branch_name):
            return False
        
        # Add files and push (pass None to use TypeScript-style "add all" behavior)
        return self.add_files_and_push(branch_name, commit_message, None)
