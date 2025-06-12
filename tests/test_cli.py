"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.cli import create_parser, main


class TestCLI:
    """Test cases for CLI functionality."""

    def test_parse_args_default(self) -> None:
        """Test argument parsing with default values."""
        parser = create_parser()
        args = parser.parse_args([])
        
        assert args.config == Path(".github/repo-file-sync.yaml")
        assert args.output == Path("./synced-files")
        assert args.verbose is False
        assert args.dry_run is False
        assert args.test_connection is False

    def test_parse_args_all_options(self) -> None:
        """Test argument parsing with all options."""
        parser = create_parser()
        args = parser.parse_args([
            "--config", "custom-config.yaml",
            "--output", "custom-output",
            "--verbose",
            "--dry-run",
            "--test-connection"
        ])
        
        assert args.config == Path("custom-config.yaml")
        assert args.output == Path("custom-output")
        assert args.verbose is True
        assert args.dry_run is True
        assert args.test_connection is True

    def test_parse_args_short_options(self) -> None:
        """Test argument parsing with short options."""
        parser = create_parser()
        args = parser.parse_args([
            "-c", "config.yaml",
            "-o", "output",
            "-v"
        ])
        
        assert args.config == Path("config.yaml")
        assert args.output == Path("output")
        assert args.verbose is True

    @patch("src.cli.RepoFileSync")
    @patch("src.cli.load_config")
    def test_main_successful_sync(self, mock_load_config: Mock, mock_sync_class: Mock, tmp_path: Path) -> None:
        """Test successful main execution."""
        # Mock configuration
        mock_config = {
            "envs": [{"name": "TEST_VAR", "value": "test_value"}],
            "envs_file": "envs.yaml",
            "sources": [{"repo": "test/repo", "ref": "main", "files": ["README.md"]}]
        }
        mock_load_config.return_value = mock_config

        # Mock sync instance
        mock_sync_instance = Mock()
        mock_result = Mock()
        mock_result.is_success = True
        mock_sync_instance.sync.return_value = mock_result
        mock_sync_class.return_value.__enter__.return_value = mock_sync_instance

        # Create test config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test config", encoding="utf-8")

        # Test successful execution
        with patch("sys.argv", ["repo-file-sync", "--config", str(config_file), "--output", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("src.cli.RepoFileSync")
    def test_main_test_connectivity_success(self, mock_sync_class: Mock) -> None:
        """Test main execution with connectivity test (success)."""
        mock_sync_instance = Mock()
        mock_sync_instance.test_connectivity.return_value = True
        mock_sync_class.return_value.__enter__.return_value = mock_sync_instance

        with patch("sys.argv", ["repo-file-sync", "--test-connection"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("src.cli.RepoFileSync")
    def test_main_test_connectivity_failure(self, mock_sync_class: Mock) -> None:
        """Test main execution with connectivity test (failure)."""
        mock_sync_instance = Mock()
        mock_sync_instance.test_connectivity.return_value = False
        mock_sync_class.return_value.__enter__.return_value = mock_sync_instance

        with patch("sys.argv", ["repo-file-sync", "--test-connection"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("src.cli.load_config")
    def test_main_config_not_found(self, mock_load_config: Mock) -> None:
        """Test main execution when config file is not found."""
        with patch("sys.argv", ["repo-file-sync", "--config", "nonexistent.yaml"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("src.cli.RepoFileSync")
    @patch("src.cli.load_config")
    def test_main_sync_error(self, mock_load_config: Mock, mock_sync_class: Mock, tmp_path: Path) -> None:
        """Test main execution when sync fails."""
        mock_config = {
            "envs": [],
            "envs_file": "envs.yaml",
            "sources": [{"repo": "test/repo", "ref": "main", "files": ["README.md"]}]
        }
        mock_load_config.return_value = mock_config

        mock_sync_instance = Mock()
        mock_result = Mock()
        mock_result.is_success = False
        mock_sync_instance.sync.return_value = mock_result
        mock_sync_class.return_value.__enter__.return_value = mock_sync_instance

        # Create actual config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test config", encoding="utf-8")

        with patch("sys.argv", ["repo-file-sync", "--config", str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("src.cli.RepoFileSync")
    @patch("src.cli.load_config")
    def test_main_dry_run(self, mock_load_config: Mock, mock_sync_class: Mock, tmp_path: Path) -> None:
        """Test main execution in dry-run mode."""
        mock_config = {
            "envs": [{"name": "TEST", "value": "value"}],
            "envs_file": "envs.yaml",
            "sources": [{"repo": "test/repo", "ref": "main", "files": ["test.txt"]}]
        }
        mock_load_config.return_value = mock_config

        mock_sync_instance = Mock()
        mock_result = Mock()
        mock_result.is_success = True
        mock_sync_instance.sync.return_value = mock_result
        mock_sync_class.return_value.__enter__.return_value = mock_sync_instance

        config_file = tmp_path / "config.yaml"
        config_file.write_text("test", encoding="utf-8")

        with patch("sys.argv", ["repo-file-sync", "--config", str(config_file), "--dry-run"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        # Verify dry-run was passed to sync
        mock_sync_instance.sync.assert_called_once()
        call_args = mock_sync_instance.sync.call_args
        assert call_args[1]["dry_run"] is True

    def test_parse_args_help(self) -> None:
        """Test that help option works."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_parse_args_timeout(self) -> None:
        """Test timeout option parsing."""
        parser = create_parser()
        args = parser.parse_args(["--timeout", "60"])
        assert args.timeout == 60

    def test_parse_args_preserve_structure(self) -> None:
        """Test preserve-structure option parsing."""
        parser = create_parser()
        args = parser.parse_args(["--preserve-structure"])
        assert args.preserve_structure is True