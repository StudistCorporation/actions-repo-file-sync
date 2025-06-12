"""Command-line interface for repo-file-sync.

This module provides the CLI commands and options for the file synchronization tool.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

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


@click.command()
@click.option(
    "--config", 
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=Path(".github/repo-file-sync.yaml"),
    help="Path to the configuration YAML file",
    show_default=True,
)
@click.option(
    "--output", 
    "-o",
    type=click.Path(path_type=Path),
    default=Path("./synced-files"),
    help="Output directory for downloaded files",
    show_default=True,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be downloaded without actually downloading",
)
@click.option(
    "--preserve-structure", 
    is_flag=True,
    help="Preserve repository directory structure (default: save all files in output directory)",
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Request timeout in seconds",
    show_default=True,
)
@click.option(
    "--verbose", 
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--test-connection",
    is_flag=True,
    help="Test GitHub connectivity and exit",
)
def main(
    config: Path,
    output: Path,
    dry_run: bool,
    preserve_structure: bool,
    timeout: int,
    verbose: bool,
    test_connection: bool,
) -> None:
    """Synchronize files from GitHub repositories based on YAML configuration.
    
    This tool reads a YAML configuration file that specifies GitHub repositories,
    git references, and file paths to download. It then fetches these files and
    saves them to a local directory.
    
    The configuration file should have this structure:
    
    \b
    sources:
      - repo: owner/repository
        ref: main
        files:
          - path/to/file.txt
          - another/file.md
    
    Examples:
    
    \b
    # Download files using default config
    python -m src.cli
    
    \b
    # Use custom config and output directory
    python -m src.cli -c my-config.yaml -o ./downloads
    
    \b
    # Dry run to see what would be downloaded
    python -m src.cli --dry-run
    
    \b
    # Preserve repository directory structure
    python -m src.cli --preserve-structure
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Test connection if requested
        if test_connection:
            with RepoFileSync(timeout=timeout) as sync:
                is_connected = sync.test_connectivity()
                sys.exit(0 if is_connected else 1)
        
        # Load and validate configuration
        logger.info(f"Loading configuration from {config}")
        try:
            config_data = load_config(config)
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
        with RepoFileSync(timeout=timeout) as sync:
            result = sync.sync(
                config_data,
                output,
                dry_run=dry_run,
                preserve_structure=preserve_structure,
            )
        
        # Report results
        if result.is_success:
            logger.info(f"✓ Sync completed successfully: {result}")
            if not dry_run:
                logger.info(f"Files saved to: {output.absolute()}")
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
        if verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()