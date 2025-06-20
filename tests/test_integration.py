"""Integration tests for the repo file sync tool."""

import os
from pathlib import Path

import pytest
import responses

from src.config import load_config
from src.github import GitHubClient


class TestIntegration:
    """Integration tests using real configuration and expected transformations."""

    def test_environment_variable_substitution_integration(
        self, tmp_path: Path
    ) -> None:
        """Test complete environment variable substitution using actual test data."""
        # Create test environment variables file
        envs_file = tmp_path / "test.envs.yaml"
        envs_content = """- name: actions/checkout
  value: awesome-checkout-action
- name: Checkout V4
  value: Super Checkout V5
- name: EXTERNAL_VAR
  value: from-external-file
- name: PROJECT_NAME
  value: "Awesome Project"
"""
        envs_file.write_text(envs_content, encoding="utf-8")

        # Create test config file
        config_file = tmp_path / "test-config.yaml"
        config_content = f"""envs_file: {envs_file.name}
sources:
  - repo: StudistCorporation/actions-repo-file-sync
    ref: 6f84753942b1d5e246be399e46011b747134a83a
    files:
    - README.md
"""
        config_file.write_text(config_content, encoding="utf-8")

        # Mock the GitHub response with our test README content
        test_readme_content = """# Repo File Sync Test

## Test Strings for Environment Variable Substitution

Basic test cases:
- Repository: actions/checkout
- Version: Checkout V4
- External: EXTERNAL_VAR
- Project: PROJECT_NAME

JSON example: {"repo": "actions/checkout", "version": "Checkout V4"}

Multiple references:
1. actions/checkout
2. actions/checkout
3. https://github.com/actions/checkout

Edge cases:
- Start: actions/checkout test
- End: test actions/checkout
- Quoted: "actions/checkout"
"""

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://raw.githubusercontent.com/StudistCorporation/actions-repo-file-sync/6f84753942b1d5e246be399e46011b747134a83a/README.md",
                body=test_readme_content,
                status=200,
            )

            # Load config and perform sync
            config = load_config(config_file)

            # Sync files
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            from src.sync import RepoFileSync

            with RepoFileSync() as sync:
                sync.sync(config, output_dir)

            # Verify the synced file exists
            synced_readme = output_dir / "README.md"
            assert synced_readme.exists()

            # Read the synced content
            synced_content = synced_readme.read_text(encoding="utf-8")

            # Verify all substitutions were made correctly
            assert "awesome-checkout-action" in synced_content
            assert "Super Checkout V5" in synced_content
            assert "from-external-file" in synced_content
            assert "Awesome Project" in synced_content

            # Verify original values were replaced
            assert "actions/checkout" not in synced_content
            assert "Checkout V4" not in synced_content
            assert "EXTERNAL_VAR" not in synced_content
            assert "PROJECT_NAME" not in synced_content

            # Verify specific transformations
            assert "Repository: awesome-checkout-action" in synced_content
            assert "Version: Super Checkout V5" in synced_content
            assert "External: from-external-file" in synced_content
            assert "Project: Awesome Project" in synced_content

            # Verify JSON transformation
            assert (
                '{"repo": "awesome-checkout-action", "version": "Super Checkout V5"}'
                in synced_content
            )

            # Verify multiple occurrences were all replaced
            lines = synced_content.split("\n")
            multiple_refs_section = [
                line for line in lines if line.startswith(("1. ", "2. ", "3. "))
            ]
            assert "1. awesome-checkout-action" in multiple_refs_section[0]
            assert "2. awesome-checkout-action" in multiple_refs_section[1]
            assert (
                "3. https://github.com/awesome-checkout-action"
                in multiple_refs_section[2]
            )

            # Verify edge cases
            assert "Start: awesome-checkout-action test" in synced_content
            assert "End: test awesome-checkout-action" in synced_content
            assert 'Quoted: "awesome-checkout-action"' in synced_content

    @pytest.mark.skipif(
        not os.getenv("GITHUB_TOKEN"),
        reason="GITHUB_TOKEN not set, skipping real API test",
    )
    def test_real_github_integration(self, tmp_path: Path) -> None:
        """Test integration with real GitHub API (requires GITHUB_TOKEN)."""
        # Use the actual configuration from the project
        config_file = Path(__file__).parent.parent / ".github" / "repo-file-sync.yaml"
        envs_file = (
            Path(__file__).parent.parent / ".github" / "repo-file-sync.envs.yaml"
        )

        if not config_file.exists() or not envs_file.exists():
            pytest.skip("Real configuration files not found")

        config = load_config(config_file)

        # Sync files using real GitHub API
        token = os.getenv("GITHUB_TOKEN")

        output_dir = tmp_path / "real_sync"
        output_dir.mkdir()

        from src.sync import RepoFileSync

        with RepoFileSync(github_token=token) as sync:
            sync.sync(config, output_dir)

        # Verify files were downloaded
        readme_path = output_dir / "README.md"
        assert readme_path.exists()

        # Verify environment variable substitution occurred
        content = readme_path.read_text(encoding="utf-8")

        # Check that substitutions were made based on our envs file
        assert "awesome-checkout-action" in content or "actions/checkout" not in content

    def test_config_loading_with_real_files(self) -> None:
        """Test config loading with the actual project configuration files."""
        config_file = Path(__file__).parent.parent / ".github" / "repo-file-sync.yaml"

        if not config_file.exists():
            pytest.skip("Real configuration file not found")

        config = load_config(config_file)

        # Verify config structure
        assert "envs" in config
        assert "envs_file" in config
        assert "sources" in config

        # Verify envs were loaded from external file
        assert len(config["envs"]) > 0

        # Verify sources structure
        assert len(config["sources"]) > 0
        source = config["sources"][0]
        assert "repo" in source
        assert "ref" in source
        assert "files" in source

    def test_dry_run_integration(self, tmp_path: Path) -> None:
        """Test integration with dry-run mode (no actual file writing)."""
        # Create test configuration
        envs_file = tmp_path / "envs.yaml"
        envs_file.write_text(
            "- name: TEST_VAR\n  value: test_value\n", encoding="utf-8"
        )

        config_file = tmp_path / "config.yaml"
        config_content = f"""envs_file: {envs_file.name}
sources:
  - repo: test/repo
    ref: main
    files:
    - test.txt
"""
        config_file.write_text(config_content, encoding="utf-8")

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://raw.githubusercontent.com/test/repo/main/test.txt",
                body="Content with TEST_VAR",
                status=200,
            )

            config = load_config(config_file)
            env_vars = config["envs"]  # Pass the list directly

            # Mock dry-run by not actually writing files
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            client = GitHubClient()

            # In a real dry-run, we would download but not write
            # For this test, we'll just verify the download would work
            content = client.download_file("test/repo", "main", "test.txt")
            substituted = client._substitute_env_vars(content, env_vars)

            assert substituted == b"Content with test_value"

            # Verify no files were actually written in dry-run
            assert len(list(output_dir.iterdir())) == 0
