"""Tests for GitHub client module."""

from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from src.github import GitHubClient


class TestGitHubClient:
    """Test cases for GitHubClient."""

    def test_init_without_token(self) -> None:
        """Test GitHubClient initialization without token."""
        client = GitHubClient()
        assert client.token is None

    def test_init_with_token(self) -> None:
        """Test GitHubClient initialization with token."""
        token = "ghp_test_token"
        client = GitHubClient(token=token)
        assert client.token == token

    @responses.activate
    def test_download_file_success_raw_url(self) -> None:
        """Test successful file download using raw URL."""
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/owner/repo/main/README.md",
            body="# Test Content",
            status=200,
        )

        client = GitHubClient()
        content = client.download_file("owner/repo", "main", "README.md")
        assert content == b"# Test Content"

    @responses.activate
    def test_download_file_fallback_to_api(self) -> None:
        """Test file download fallback to API when raw URL fails."""
        # Mock raw URL failure
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/owner/repo/main/README.md",
            status=404,
        )

        # Mock API success
        api_response = {
            "content": "IyBUZXN0IENvbnRlbnQ=",  # base64 encoded "# Test Content"
            "encoding": "base64",
        }
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/contents/README.md",
            json=api_response,
            status=200,
        )

        client = GitHubClient(token="test_token")
        content = client.download_file("owner/repo", "main", "README.md")
        assert content == b"# Test Content"

    @responses.activate
    def test_download_file_with_token(self) -> None:
        """Test file download with authentication token."""
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/owner/repo/main/README.md",
            body="# Private Content",
            status=200,
        )

        client = GitHubClient(token="ghp_test_token")
        content = client.download_file("owner/repo", "main", "README.md")
        assert content == b"# Private Content"

        # Verify token was used in request
        assert len(responses.calls) == 1
        assert "Authorization" in responses.calls[0].request.headers
        assert responses.calls[0].request.headers["Authorization"] == "token ghp_test_token"

    @responses.activate
    def test_download_file_both_methods_fail(self) -> None:
        """Test file download when both raw URL and API fail."""
        # Mock raw URL failure
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/owner/repo/main/README.md",
            status=404,
        )

        # Mock API failure
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/contents/README.md",
            status=404,
        )

        client = GitHubClient(token="test_token")
        with pytest.raises(FileNotFoundError, match="File not found"):
            client.download_file("owner/repo", "main", "README.md")

    def test_substitute_env_vars(self) -> None:
        """Test environment variable substitution in file content."""
        client = GitHubClient()
        content = b"Repository: actions/checkout\nVersion: Checkout V4"
        env_vars = {
            "actions/checkout": "awesome-checkout-action",
            "Checkout V4": "Super Checkout V5",
        }

        result = client._substitute_env_vars(content, env_vars)
        expected = b"Repository: awesome-checkout-action\nVersion: Super Checkout V5"
        assert result == expected

    def test_substitute_env_vars_no_matches(self) -> None:
        """Test environment variable substitution with no matches."""
        client = GitHubClient()
        content = b"No variables here"
        env_vars = {"VAR1": "value1", "VAR2": "value2"}

        result = client._substitute_env_vars(content, env_vars)
        assert result == content

    def test_substitute_env_vars_multiple_occurrences(self) -> None:
        """Test environment variable substitution with multiple occurrences."""
        client = GitHubClient()
        content = b"actions/checkout and actions/checkout again"
        env_vars = {"actions/checkout": "awesome-action"}

        result = client._substitute_env_vars(content, env_vars)
        expected = b"awesome-action and awesome-action again"
        assert result == expected

    def test_substitute_env_vars_with_quotes(self) -> None:
        """Test environment variable substitution with quoted content."""
        client = GitHubClient()
        content = b'{"repo": "actions/checkout", "version": "Checkout V4"}'
        env_vars = {
            "actions/checkout": "awesome-checkout-action",
            "Checkout V4": "Super Checkout V5",
        }

        result = client._substitute_env_vars(content, env_vars)
        expected = b'{"repo": "awesome-checkout-action", "version": "Super Checkout V5"}'
        assert result == expected

    def test_substitute_env_vars_binary_content(self) -> None:
        """Test environment variable substitution skips binary content."""
        client = GitHubClient()
        # Binary content that can't be decoded as UTF-8
        content = b"\x89PNG\r\n\x1a\n"
        env_vars = {"test": "replacement"}

        result = client._substitute_env_vars(content, env_vars)
        # Should return original content unchanged
        assert result == content

    @responses.activate
    def test_download_file_with_env_substitution(self, tmp_path: Path) -> None:
        """Test file download with environment variable substitution."""
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/test/repo/main/config.yaml",
            body="repo: actions/checkout\nversion: Checkout V4",
            status=200,
        )

        client = GitHubClient()
        env_vars = {
            "actions/checkout": "awesome-checkout-action",
            "Checkout V4": "Super Checkout V5",
        }
        
        output_path = tmp_path / "config.yaml"
        content = client.download_file(
            "test/repo", "main", "config.yaml", output_path=output_path, env_vars=env_vars
        )
        
        expected = b"repo: awesome-checkout-action\nversion: Super Checkout V5"
        assert content == expected
        
        # Verify file was saved
        assert output_path.exists()
        saved_content = output_path.read_bytes()
        assert saved_content == expected

    @responses.activate
    def test_test_connection_success(self) -> None:
        """Test connectivity test success."""
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/actions/checkout/main/README.md",
            status=200,
        )

        client = GitHubClient()
        result = client.test_connection()
        assert result is True

    @responses.activate
    def test_test_connection_failure(self) -> None:
        """Test connectivity test failure."""
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/actions/checkout/main/README.md",
            status=500,
        )

        client = GitHubClient()
        result = client.test_connection()
        assert result is False

    def test_context_manager(self) -> None:
        """Test GitHubClient as context manager."""
        with GitHubClient() as client:
            assert client.session is not None
        # Session should be closed after exiting context

    def test_save_file_creates_directories(self, tmp_path: Path) -> None:
        """Test that save_file creates parent directories."""
        client = GitHubClient()
        content = b"test content"
        output_path = tmp_path / "subdir" / "test.txt"
        
        # Directory doesn't exist yet
        assert not output_path.parent.exists()
        
        client._save_file(content, output_path)
        
        # Directory should be created and file should exist
        assert output_path.exists()
        assert output_path.read_bytes() == content

    @responses.activate  
    def test_download_file_url_encoding(self) -> None:
        """Test file download with special characters in path."""
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/owner/repo/main/path%20with%20spaces/file.txt",
            body="content",
            status=200,
        )

        client = GitHubClient()
        content = client.download_file("owner/repo", "main", "path with spaces/file.txt")
        assert content == b"content"

    def test_timeout_configuration(self) -> None:
        """Test timeout configuration."""
        client = GitHubClient(timeout=60)
        assert client.timeout == 60

    @patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"})
    def test_token_from_environment(self) -> None:
        """Test token loading from environment variable."""
        client = GitHubClient()
        assert client.token == "env_token"