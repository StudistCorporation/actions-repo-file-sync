"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_config_file(fixtures_dir: Path) -> Path:
    """Return the path to the test configuration file."""
    return fixtures_dir / "test-config.yaml"


@pytest.fixture
def test_envs_file(fixtures_dir: Path) -> Path:
    """Return the path to the test environment variables file."""
    return fixtures_dir / "test-envs.yaml"


@pytest.fixture
def sample_readme_content() -> str:
    """Return sample README content for testing."""
    return """# Repo File Sync Test

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


@pytest.fixture
def expected_substituted_content() -> str:
    """Return expected content after environment variable substitution."""
    return """# Repo File Sync Test

## Test Strings for Environment Variable Substitution

Basic test cases:
- Repository: awesome-checkout-action
- Version: Super Checkout V5
- External: from-external-file
- Project: Awesome Project

JSON example: {"repo": "awesome-checkout-action", "version": "Super Checkout V5"}

Multiple references:
1. awesome-checkout-action
2. awesome-checkout-action
3. https://github.com/awesome-checkout-action

Edge cases:
- Start: awesome-checkout-action test
- End: test awesome-checkout-action
- Quoted: "awesome-checkout-action"
"""
