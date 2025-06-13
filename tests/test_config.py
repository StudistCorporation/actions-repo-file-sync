"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import Config, EnvConfig, SourceConfig, load_config


def test_load_config_with_envs_file(tmp_path: Path) -> None:
    """Test loading configuration with external environment variables file."""
    # Create environment variables file
    envs_file = tmp_path / "test.envs.yaml"
    envs_data = [
        {"name": "TEST_VAR", "value": "test_value"},
        {"name": "ANOTHER_VAR", "value": "another_value"},
    ]
    with envs_file.open("w", encoding="utf-8") as f:
        yaml.dump(envs_data, f)

    # Create main config file
    config_file = tmp_path / "config.yaml"
    config_data = {
        "envs_file": "test.envs.yaml",
        "sources": [
            {
                "repo": "owner/repo",
                "ref": "main",
                "files": ["README.md", "LICENSE"],
            }
        ],
    }
    with config_file.open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    # Load and verify config
    config = load_config(config_file)

    assert len(config["envs"]) == 2
    assert config["envs"][0]["name"] == "TEST_VAR"
    assert config["envs"][0]["value"] == "test_value"
    assert config["envs"][1]["name"] == "ANOTHER_VAR"
    assert config["envs"][1]["value"] == "another_value"

    assert len(config["sources"]) == 1
    assert config["sources"][0]["repo"] == "owner/repo"
    assert config["sources"][0]["ref"] == "main"
    assert config["sources"][0]["files"] == ["README.md", "LICENSE"]


def test_load_config_missing_envs_file() -> None:
    """Test that loading config fails when envs_file is missing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "envs_file": "nonexistent.yaml",
            "sources": [{"repo": "owner/repo", "ref": "main", "files": ["README.md"]}],
        }
        yaml.dump(config_data, f)
        config_file = Path(f.name)

    with pytest.raises(FileNotFoundError, match="Environment variables file not found"):
        load_config(config_file)

    config_file.unlink()


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Test that loading config fails with invalid YAML."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content: [", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_config(config_file)


def test_load_config_missing_required_fields(tmp_path: Path) -> None:
    """Test that loading config fails when required fields are missing."""
    # Create valid envs file
    envs_file = tmp_path / "envs.yaml"
    envs_file.write_text("[]", encoding="utf-8")

    # Create config without required sources field
    config_file = tmp_path / "config.yaml"
    config_data = {"envs_file": "envs.yaml"}
    with config_file.open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ValueError, match="Configuration must contain 'sources' key"):
        load_config(config_file)


def test_config_types() -> None:
    """Test that config types are properly structured."""
    env_config: EnvConfig = {"name": "TEST", "value": "value"}
    assert env_config["name"] == "TEST"
    assert env_config["value"] == "value"

    source_config: SourceConfig = {
        "repo": "owner/repo",
        "ref": "main",
        "files": ["file1.txt", "file2.txt"],
    }
    assert source_config["repo"] == "owner/repo"
    assert source_config["ref"] == "main"
    assert source_config["files"] == ["file1.txt", "file2.txt"]

    config: Config = {
        "envs": [env_config],
        "envs_file": "envs.yaml",
        "sources": [source_config],
    }
    assert len(config["envs"]) == 1
    assert config["envs_file"] == "envs.yaml"
    assert len(config["sources"]) == 1


def test_load_config_with_relative_envs_file(tmp_path: Path) -> None:
    """Test loading config with relative path to envs_file."""
    # Create subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    # Create envs file in subdirectory
    envs_file = subdir / "envs.yaml"
    envs_data = [{"name": "REL_VAR", "value": "relative_value"}]
    with envs_file.open("w", encoding="utf-8") as f:
        yaml.dump(envs_data, f)

    # Create config file pointing to relative envs file
    config_file = tmp_path / "config.yaml"
    config_data = {
        "envs_file": "subdir/envs.yaml",
        "sources": [{"repo": "test/repo", "ref": "main", "files": ["test.txt"]}],
    }
    with config_file.open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    # Load and verify config
    config = load_config(config_file)

    assert len(config["envs"]) == 1
    assert config["envs"][0]["name"] == "REL_VAR"
    assert config["envs"][0]["value"] == "relative_value"
