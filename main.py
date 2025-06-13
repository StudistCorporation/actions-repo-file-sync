"""Main entry point for repo-file-sync CLI tool.

This module provides the main entry point for the command-line interface
of the repository file synchronization tool.
"""

import os
from src.cli import main

def main_with_env_parsing() -> None:
    """Main entry point that handles GitHub Actions environment variables."""
    import logging
    
    # Setup basic logging to ensure debug messages appear
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)
    
    # Debug: Print environment variables
    logger.info(f"DEBUG: INPUT_CREATE_PR = {os.getenv('INPUT_CREATE_PR', 'NOT_SET')}")
    logger.info(f"DEBUG: INPUT_DRY_RUN = {os.getenv('INPUT_DRY_RUN', 'NOT_SET')}")
    print(f"DEBUG: INPUT_CREATE_PR = {os.getenv('INPUT_CREATE_PR', 'NOT_SET')}")
    print(f"DEBUG: INPUT_DRY_RUN = {os.getenv('INPUT_DRY_RUN', 'NOT_SET')}")
    
    # Parse GitHub Actions environment variables
    create_pr_env = os.getenv("INPUT_CREATE_PR", "false").lower()
    logger.info(f"DEBUG: create_pr_env = {create_pr_env}")
    
    if create_pr_env == "true":
        os.environ.setdefault("CREATE_PR", "true")
        logger.info("DEBUG: Set CREATE_PR environment variable")
    if os.getenv("INPUT_PR_TITLE"):
        os.environ.setdefault("PR_TITLE", os.getenv("INPUT_PR_TITLE"))
    if os.getenv("INPUT_PR_BODY"):
        os.environ.setdefault("PR_BODY", os.getenv("INPUT_PR_BODY"))
    if os.getenv("INPUT_BRANCH_NAME"):
        os.environ.setdefault("BRANCH_NAME", os.getenv("INPUT_BRANCH_NAME"))
    
    # Build command line arguments from environment
    import sys
    
    # Add PR-related arguments if set
    if create_pr_env == "true":
        sys.argv.append("--create-pr")
        logger.info("DEBUG: Added --create-pr to sys.argv")
    
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
    
    # Debug: Print final sys.argv
    logger.info(f"DEBUG: Final sys.argv = {sys.argv}")
    print(f"DEBUG: Final sys.argv = {sys.argv}")
    
    main()

if __name__ == "__main__":
    main_with_env_parsing()
