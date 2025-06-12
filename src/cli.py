"""Command-line interface for repo-file-sync.

This module provides the CLI commands and options for the file synchronization tool.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .sync import RepoFileSync


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Enable debug logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[logging.StreamHandler()]
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Synchronize files from GitHub repositories based on YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download files using default config
  python main.py

  # Use custom config and output directory
  python main.py -c my-config.yaml -o ./downloads

  # Dry run to see what would be downloaded
  python main.py --dry-run

  # Preserve repository directory structure
  python main.py --preserve-structure
        """.strip()
    )
    
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path(".github/repo-file-sync.yaml"),
        help="Path to the configuration YAML file (default: .github/repo-file-sync.yaml)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./synced-files"),
        help="Output directory for downloaded files (default: ./synced-files)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Preserve repository directory structure (default: save all files in output directory)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test GitHub connectivity and exit"
    )
    
    return parser


def main() -> None:
    """Main entry point for the CLI application."""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate config file exists if not testing connection
    if not args.test_connection and not args.config.exists():
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    
    try:
        # Test connection if requested
        if args.test_connection:
            with RepoFileSync(timeout=args.timeout) as sync:
                is_connected = sync.test_connectivity()
                sys.exit(0 if is_connected else 1)
        
        # Load and validate configuration
        logger.info(f"Loading configuration from {args.config}")
        try:
            config_data = load_config(args.config)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
        
        # Log configuration summary
        total_files = sum(len(source["files"]) for source in config_data["sources"])
        logger.info(
            f"Configuration loaded: {len(config_data['sources'])} sources, "
            f"{total_files} files to sync"
        )
        
        # Perform synchronization
        with RepoFileSync(timeout=args.timeout) as sync:
            result = sync.sync(
                config_data,
                args.output,
                dry_run=args.dry_run,
                preserve_structure=args.preserve_structure,
            )
        
        # Report results
        if result.is_success:
            logger.info(f"✓ Sync completed successfully: {result}")
            if not args.dry_run:
                logger.info(f"Files saved to: {args.output.absolute()}")
        else:
            logger.error(f"✗ Sync completed with errors: {result}")
            
            # Log detailed error information
            for file_path, error in result.failed_files:
                logger.error(f"  {file_path}: {error}")
        
        # Exit with appropriate code
        sys.exit(0 if result.is_success else 1)
        
    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()