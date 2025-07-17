"""File synchronization logic for repo-file-sync.

This module orchestrates the process of downloading files from GitHub repositories
based on the configuration and saving them to the local filesystem.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config import Config, SourceConfig
from .github import GitHubClient

logger = logging.getLogger(__name__)


class SyncResult:
    """Result of a file synchronization operation.

    Contains information about successful and failed file downloads.
    """

    def __init__(self):
        """Initialize empty sync result."""
        self.successful_files: list[str] = []
        self.failed_files: list[tuple[str, Exception]] = []
        self.total_bytes = 0

    def add_success(self, file_path: str, size_bytes: int) -> None:
        """Record a successful file download.

        Args:
            file_path: Path of the successfully downloaded file
            size_bytes: Size of the downloaded file in bytes
        """
        self.successful_files.append(file_path)
        self.total_bytes += size_bytes

    def add_failure(self, file_path: str, error: Exception) -> None:
        """Record a failed file download.

        Args:
            file_path: Path of the file that failed to download
            error: Exception that caused the failure
        """
        self.failed_files.append((file_path, error))

    @property
    def success_count(self) -> int:
        """Number of successfully downloaded files."""
        return len(self.successful_files)

    @property
    def failure_count(self) -> int:
        """Number of failed file downloads."""
        return len(self.failed_files)

    @property
    def is_success(self) -> bool:
        """True if all files were downloaded successfully."""
        return self.failure_count == 0

    def __str__(self) -> str:
        """String representation of sync results."""
        return (
            f"Sync completed: {self.success_count} successful, "
            f"{self.failure_count} failed, {self.total_bytes} bytes downloaded"
        )


class RepoFileSync:
    """Main synchronization orchestrator.

    Handles the process of downloading files from multiple GitHub repositories
    based on configuration and organizing them in the local filesystem.
    """

    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        timeout: int = 30,
        github_token: Optional[str] = None,
    ):
        """Initialize the file synchronizer.

        Args:
            github_client: Optional GitHub client instance
            timeout: Request timeout in seconds
            github_token: Optional GitHub token for private repository access
        """
        self.github_client = github_client or GitHubClient(
            timeout=timeout, token=github_token
        )
        self._owns_client = github_client is None

    def sync(
        self,
        config: Config,
        output_dir: Path,
        dry_run: bool = False,
        preserve_structure: bool = False,
    ) -> SyncResult:
        """Synchronize files from GitHub repositories.

        Downloads all files specified in the configuration from their respective
        GitHub repositories and saves them to the output directory.

        Args:
            config: Configuration specifying which files to download
            output_dir: Directory to save downloaded files
            dry_run: If True, only log what would be downloaded without doing it
            preserve_structure: If True, maintain repository structure in output

        Returns:
            Result object containing success/failure information

        Example:
            >>> sync = RepoFileSync()
            >>> config = {"sources": [{"repo": "actions/checkout", "ref": "main", "files": ["README.md"]}]}
            >>> result = sync.sync(config, Path("./downloads"))
            >>> print(result.success_count)
            1
        """
        result = SyncResult()

        logger.info(f"Starting sync to {output_dir}")
        if dry_run:
            logger.info("DRY RUN MODE - No files will be downloaded")

        # Create output directory if it doesn't exist
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Build environment variables dictionary
        env_vars = {env["name"]: env["value"] for env in config["envs"]}
        if env_vars:
            logger.info(f"Using {len(env_vars)} environment variables for substitution")

        # Process each source repository
        for source in config["sources"]:
            logger.info(f"Processing source: {source['repo']} ({source['ref']})")

            source_result = self._sync_source(
                source, output_dir, dry_run, preserve_structure, env_vars
            )

            # Merge results
            result.successful_files.extend(source_result.successful_files)
            result.failed_files.extend(source_result.failed_files)
            result.total_bytes += source_result.total_bytes

        logger.info(str(result))
        return result

    def _sync_source(
        self,
        source: SourceConfig,
        output_dir: Path,
        dry_run: bool,
        preserve_structure: bool,
        env_vars: dict[str, str],
    ) -> SyncResult:
        """Synchronize files from a single source repository.

        Args:
            source: Source configuration
            output_dir: Output directory
            dry_run: Whether this is a dry run
            preserve_structure: Whether to preserve directory structure
            env_vars: Environment variables for content substitution

        Returns:
            Sync result for this source
        """
        result = SyncResult()
        repo = source["repo"]
        ref = source["ref"]

        for file_path in source["files"]:
            full_file_id = f"{repo}:{ref}:{file_path}"

            try:
                if dry_run:
                    logger.info(f"Would download {full_file_id}")
                    result.add_success(full_file_id, 0)  # Unknown size in dry run
                    continue

                # Determine output path
                if preserve_structure:
                    # Create subdirectory for each repo
                    repo_dir = output_dir / repo.replace("/", "_")
                    output_path = repo_dir / file_path
                else:
                    # Flatten structure - save all files directly in output directory
                    filename = Path(file_path).name
                    output_path = output_dir / filename

                # Download the file
                content = self.github_client.download_file(
                    repo, ref, file_path, output_path, env_vars
                )

                # Check if file was actually written or skipped
                file_written = getattr(self.github_client, "last_file_written", True)

                result.add_success(full_file_id, len(content))
                if file_written:
                    logger.info(f"✓ Downloaded {full_file_id} -> {output_path}")
                else:
                    logger.info(
                        f"✓ Skipped {full_file_id} -> {output_path} (identical content)"
                    )

            except Exception as e:
                result.add_failure(full_file_id, e)
                logger.error(f"✗ Failed to download {full_file_id}: {e}")

        return result

    def test_connectivity(self) -> bool:
        """Test connectivity to GitHub.

        Returns:
            True if GitHub is accessible, False otherwise
        """
        logger.info("Testing GitHub connectivity...")
        is_connected = self.github_client.test_connection()

        if is_connected:
            logger.info("✓ GitHub connectivity test passed")
        else:
            logger.error("✗ GitHub connectivity test failed")

        return is_connected

    def close(self) -> None:
        """Clean up resources.

        Should be called when done using the synchronizer.
        """
        if self._owns_client:
            self.github_client.close()

    def __enter__(self) -> RepoFileSync:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
