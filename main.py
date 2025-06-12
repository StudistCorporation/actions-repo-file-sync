"""Main entry point for repo-file-sync CLI tool.

This module provides the main entry point for the command-line interface
of the repository file synchronization tool.
"""

import os
from src.cli import main

def main_with_env_parsing() -> None:
    """Main entry point that handles GitHub Actions environment variables."""
    import sys
    
    # Debug: Print all INPUT_ environment variables
    print("DEBUG: Environment variables:")
    for key, value in os.environ.items():
        if key.startswith("INPUT_"):
            print(f"  {key}={value}")
    
    # GitHub Actions converts hyphens to underscores in environment variable names
    # action.yml: create-pr -> INPUT_CREATE_PR
    
    # Add config argument
    if os.getenv("INPUT_CONFIG"):
        sys.argv.extend(["--config", os.getenv("INPUT_CONFIG")])
    
    # Add dry-run argument
    if os.getenv("INPUT_DRY_RUN", "false").lower() == "true":
        sys.argv.append("--dry-run")
    
    # Add PR-related arguments
    if os.getenv("INPUT_CREATE_PR", "false").lower() == "true":
        sys.argv.append("--create-pr")
        print("DEBUG: Adding --create-pr flag")
    
    if os.getenv("INPUT_PR_TITLE"):
        sys.argv.extend(["--pr-title", os.getenv("INPUT_PR_TITLE")])
        print(f"DEBUG: Adding --pr-title '{os.getenv('INPUT_PR_TITLE')}'")
    
    if os.getenv("INPUT_PR_BODY"):
        sys.argv.extend(["--pr-body", os.getenv("INPUT_PR_BODY")])
        print("DEBUG: Adding --pr-body")
    
    if os.getenv("INPUT_BRANCH_NAME"):
        sys.argv.extend(["--branch-name", os.getenv("INPUT_BRANCH_NAME")])
        print(f"DEBUG: Adding --branch-name '{os.getenv('INPUT_BRANCH_NAME')}'")
    
    # Enable verbose logging for debugging
    sys.argv.append("--verbose")
    
    print(f"DEBUG: Final sys.argv: {sys.argv}")
    
    main()

if __name__ == "__main__":
    main_with_env_parsing()
