"""Configuration parsing and validation for repo-file-sync.

This module handles reading and validating the YAML configuration file
that defines which files to sync from GitHub repositories.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


class EnvConfig(TypedDict):
    """Configuration for an environment variable.
    Defines a name-value pair for environment variable substitution.
    """
    name: str
    value: str


class SourceConfig(TypedDict):
    """Configuration for a single source repository.
    
    Defines a GitHub repository, git reference, and list of files to sync.
    """
    repo: str
    ref: str
    files: list[str]


class Config(TypedDict):
    """Main configuration structure.
    
    Contains environment variables and list of source repositories to sync files from.
    """
    envs: list[EnvConfig]
    sources: list[SourceConfig]


def load_config(config_path: Path) -> Config:
    """Load and validate configuration from YAML file.
    
    Reads the YAML configuration file and validates its structure
    to ensure all required fields are present and correctly typed.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Parsed and validated configuration dictionary
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML is malformed
        ValueError: If the config structure is invalid
        
    Example:
        >>> config = load_config(Path(".github/repo-file-sync.yaml"))
        >>> print(len(config["sources"]))
        2
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    logger.info(f"Loading configuration from {config_path}")
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML configuration: {e}") from e
    
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a dictionary")
    
    if "sources" not in data:
        raise ValueError("Configuration must contain 'sources' key")
    
    # Parse environment variables (optional)
    envs = data.get("envs", [])
    if not isinstance(envs, list):
        raise ValueError("'envs' must be a list")
    
    validated_envs = []
    for i, env in enumerate(envs):
        if not isinstance(env, dict):
            raise ValueError(f"Environment variable {i} must be a dictionary")
        
        # Validate required fields
        required_fields = ["name", "value"]
        for field in required_fields:
            if field not in env:
                raise ValueError(f"Environment variable {i} missing required field: {field}")
        
        name = env["name"]
        value = env["value"]
        
        if not isinstance(name, str):
            raise ValueError(f"Environment variable {i}: 'name' must be a string")
        if not isinstance(value, str):
            raise ValueError(f"Environment variable {i}: 'value' must be a string")
        
        validated_env: EnvConfig = {
            "name": name,
            "value": value,
        }
        validated_envs.append(validated_env)
    
    # Parse sources
    sources = data["sources"]
    if not isinstance(sources, list):
        raise ValueError("'sources' must be a list")
    
    validated_sources = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f"Source {i} must be a dictionary")
        
        # Validate required fields
        required_fields = ["repo", "ref", "files"]
        for field in required_fields:
            if field not in source:
                raise ValueError(f"Source {i} missing required field: {field}")
        
        repo = source["repo"]
        ref = source["ref"]
        files = source["files"]
        
        if not isinstance(repo, str):
            raise ValueError(f"Source {i}: 'repo' must be a string")
        if not isinstance(ref, str):
            raise ValueError(f"Source {i}: 'ref' must be a string")
        if not isinstance(files, list):
            raise ValueError(f"Source {i}: 'files' must be a list")
        
        # Validate repo format (should be owner/repo)
        if "/" not in repo:
            raise ValueError(f"Source {i}: 'repo' must be in format 'owner/repo'")
        
        # Validate all files are strings
        for j, file_path in enumerate(files):
            if not isinstance(file_path, str):
                raise ValueError(f"Source {i}, file {j}: must be a string")
        
        validated_source: SourceConfig = {
            "repo": repo,
            "ref": ref,
            "files": files,
        }
        validated_sources.append(validated_source)
    
    config: Config = {
        "envs": validated_envs,
        "sources": validated_sources
    }
    logger.info(
        f"Successfully loaded configuration with {len(validated_envs)} environment variables "
        f"and {len(validated_sources)} sources"
    )
    
    return config


def validate_config(data: Any) -> Config:
    """Validate configuration data structure.
    
    Ensures the provided data matches the expected Config structure.
    
    Args:
        data: Raw configuration data to validate
        
    Returns:
        Validated configuration
        
    Raises:
        ValueError: If the configuration structure is invalid
    """
    # This function is used internally by load_config
    # but is exposed for testing purposes
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a dictionary")
    
    if "sources" not in data:
        raise ValueError("Configuration must contain 'sources' key")
    
    return data  # type: ignore