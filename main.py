"""Main entry point for repo-file-sync CLI tool.

This module provides the main entry point for the command-line interface
of the repository file synchronization tool.
"""

import os
from src.cli import main

def main_with_env_parsing() -> None:
    """Main entry point that handles GitHub Actions environment variables."""
    # Parse GitHub Actions environment variables
    if os.getenv("INPUT_CREATE_PR", "false").lower() == "true":
        os.environ.setdefault("CREATE_PR", "true")
    if os.getenv("INPUT_PR_TITLE"):
        os.environ.setdefault("PR_TITLE", os.getenv("INPUT_PR_TITLE"))
    if os.getenv("INPUT_PR_BODY"):
        os.environ.setdefault("PR_BODY", os.getenv("INPUT_PR_BODY"))
    if os.getenv("INPUT_BRANCH_NAME"):
        os.environ.setdefault("BRANCH_NAME", os.getenv("INPUT_BRANCH_NAME"))
    
    # Build command line arguments from environment
    import sys
    
    # Add PR-related arguments if set
    if os.getenv("INPUT_CREATE_PR", "false").lower() == "true":
        sys.argv.append("--create-pr")
    
    if os.getenv("INPUT_PR_TITLE"):
        sys.argv.extend(["--pr-title", os.getenv("INPUT_PR_TITLE")])
    
    if os.getenv("INPUT_PR_BODY"):
        sys.argv.extend(["--pr-body", os.getenv("INPUT_PR_BODY")])
    
    if os.getenv("INPUT_BRANCH_NAME"):
        sys.argv.extend(["--branch-name", os.getenv("INPUT_BRANCH_NAME")])
    
    if os.getenv("INPUT_CONFIG"):
        sys.argv.extend(["--config", os.getenv("INPUT_CONFIG")])
    
    if os.getenv("INPUT_DRY_RUN", "false").lower() == "true":
        sys.argv.append("--dry-run")
    
    # Enable verbose logging for debugging
    sys.argv.append("--verbose")
    
    main()

if __name__ == "__main__":
    main_with_env_parsing()
