"""Main entry point for repo-file-sync CLI tool.

This module provides the main entry point for the command-line interface
of the repository file synchronization tool.
"""

import os
from src.cli import main

def main_with_env_parsing() -> None:
    """Main entry point that handles GitHub Actions environment variables."""
    # This is now handled by entrypoint.sh, so just call main directly
    main()

if __name__ == "__main__":
    main_with_env_parsing()
