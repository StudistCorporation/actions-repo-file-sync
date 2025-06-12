"""Repo File Sync - GitHub repository file synchronization tool.

This package provides functionality to synchronize files from GitHub repositories
based on YAML configuration files.
"""

from .config import Config, SourceConfig, load_config
from .github import GitHubClient
from .sync import RepoFileSync, SyncResult

__version__ = "2.0.0"

__all__ = [
    "Config",
    "SourceConfig", 
    "load_config",
    "GitHubClient",
    "RepoFileSync",
    "SyncResult",
]