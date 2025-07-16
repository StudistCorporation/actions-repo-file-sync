"""Tests for GitHub client module."""

from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from src.github import GitHubClient


class TestGitHubClient:
    """Test cases for GitHubClient."""

    @patch.dict("os.environ", {}, clear=True)
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
        assert (
            responses.calls[0].request.headers["Authorization"]
            == "token ghp_test_token"
        )

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
        env_vars = [
            {"name": "actions/checkout", "value": "awesome-checkout-action"},
            {"name": "Checkout V4", "value": "Super Checkout V5"},
        ]

        result = client._substitute_env_vars(content, env_vars)
        expected = b"Repository: awesome-checkout-action\nVersion: Super Checkout V5"
        assert result == expected

    def test_substitute_env_vars_no_matches(self) -> None:
        """Test environment variable substitution with no matches."""
        client = GitHubClient()
        content = b"No variables here"
        env_vars = [
            {"name": "VAR1", "value": "value1"},
            {"name": "VAR2", "value": "value2"},
        ]

        result = client._substitute_env_vars(content, env_vars)
        assert result == content

    def test_substitute_env_vars_multiple_occurrences(self) -> None:
        """Test environment variable substitution with multiple occurrences."""
        client = GitHubClient()
        content = b"actions/checkout and actions/checkout again"
        env_vars = [{"name": "actions/checkout", "value": "awesome-action"}]

        result = client._substitute_env_vars(content, env_vars)
        expected = b"awesome-action and awesome-action again"
        assert result == expected

    def test_substitute_env_vars_with_quotes(self) -> None:
        """Test environment variable substitution with quoted content."""
        client = GitHubClient()
        content = b'{"repo": "actions/checkout", "version": "Checkout V4"}'
        env_vars = [
            {"name": "actions/checkout", "value": "awesome-checkout-action"},
            {"name": "Checkout V4", "value": "Super Checkout V5"},
        ]

        result = client._substitute_env_vars(content, env_vars)
        expected = (
            b'{"repo": "awesome-checkout-action", "version": "Super Checkout V5"}'
        )
        assert result == expected

    def test_substitute_env_vars_binary_content(self) -> None:
        """Test environment variable substitution skips binary content."""
        client = GitHubClient()
        # Binary content that can't be decoded as UTF-8
        content = b"\x89PNG\r\n\x1a\n"
        env_vars = [{"name": "test", "value": "replacement"}]

        result = client._substitute_env_vars(content, env_vars)
        # Should return original content unchanged
        assert result == content

    def test_substitute_env_vars_regex(self) -> None:
        """Test environment variable substitution with regex patterns."""
        client = GitHubClient()
        content = b"v1.2.3 and version 2.0.0 and v3.1.4"
        env_vars = [
            {
                "name": r"v(\d+)\.(\d+)\.(\d+)",
                "value": r"version-$1.$2.$3",
                "regex": True,
            }
        ]

        result = client._substitute_env_vars(content, env_vars)
        expected = b"version-1.2.3 and version 2.0.0 and version-3.1.4"
        assert result == expected

    def test_substitute_env_vars_regex_case_insensitive(self) -> None:
        """Test regex substitution with case-insensitive flag."""
        client = GitHubClient()
        content = b"checkout v4 and Checkout V4 and CHECKOUT V4"
        env_vars = [
            {
                "name": r"checkout v4",
                "value": "checkout-v5",
                "regex": True,
                "flags": "i",
            }
        ]

        result = client._substitute_env_vars(content, env_vars)
        expected = b"checkout-v5 and checkout-v5 and checkout-v5"
        assert result == expected

    def test_substitute_env_vars_regex_multiline(self) -> None:
        """Test regex substitution with multiline flag."""
        client = GitHubClient()
        content = b"line1\nstart of line2\nline3"
        env_vars = [
            {"name": r"^start", "value": "beginning", "regex": True, "flags": "m"}
        ]

        result = client._substitute_env_vars(content, env_vars)
        expected = b"line1\nbeginning of line2\nline3"
        assert result == expected

    def test_substitute_env_vars_invalid_regex(self) -> None:
        """Test handling of invalid regex patterns."""
        client = GitHubClient()
        content = b"test content"
        env_vars = [{"name": r"[invalid", "value": "replacement", "regex": True}]

        # Should not raise exception, just skip invalid pattern
        result = client._substitute_env_vars(content, env_vars)
        assert result == content  # Content unchanged

    def test_substitute_env_vars_mixed_replacements(self) -> None:
        """Test mix of simple string and regex replacements."""
        client = GitHubClient()
        content = b"Repository: actions/checkout v1.0.0"
        env_vars = [
            {"name": "actions/checkout", "value": "awesome-action"},
            {
                "name": r"v(\d+)\.(\d+)\.(\d+)",
                "value": r"version $1.$2.$3",
                "regex": True,
            },
        ]

        result = client._substitute_env_vars(content, env_vars)
        expected = b"Repository: awesome-action version 1.0.0"
        assert result == expected

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
        env_vars = [
            {"name": "actions/checkout", "value": "awesome-checkout-action"},
            {"name": "Checkout V4", "value": "Super Checkout V5"},
        ]

        output_path = tmp_path / "config.yaml"
        content = client.download_file(
            "test/repo",
            "main",
            "config.yaml",
            output_path=output_path,
            env_vars=env_vars,
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
        content = client.download_file(
            "owner/repo", "main", "path with spaces/file.txt"
        )
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
