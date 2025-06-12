#!/bin/bash
# Local testing script for the GitHub Action

set -euo pipefail

echo "🧪 Testing repo-file-sync GitHub Action locally"
echo "================================================"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed. Please install Docker first."
    exit 1
fi

# Check if config file exists
CONFIG_FILE="${1:-.github/repo-file-sync.yaml}"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Configuration file not found: $CONFIG_FILE"
    echo "Usage: $0 [config-file]"
    exit 1
fi

echo "📁 Using configuration file: $CONFIG_FILE"

# Create output directory
OUTPUT_DIR="./test-synced-files"
mkdir -p "$OUTPUT_DIR"

echo "📦 Building Docker image..."
docker build -t repo-file-sync-action .

echo "🚀 Running action with test configuration..."

# Set up environment variables
export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
export GITHUB_OUTPUT="${GITHUB_OUTPUT:-/tmp/github_output}"

# Create temporary output file for GitHub Actions format
echo "" > "$GITHUB_OUTPUT"

# Run the Docker container
docker run --rm \
    -v "$(pwd)/$CONFIG_FILE:/app/$CONFIG_FILE:ro" \
    -v "$(pwd)/$OUTPUT_DIR:/app/$OUTPUT_DIR" \
    -v "$GITHUB_OUTPUT:/tmp/github_output" \
    -e GITHUB_TOKEN="$GITHUB_TOKEN" \
    -e GITHUB_OUTPUT="/tmp/github_output" \
    -e INPUT_CONFIG="$CONFIG_FILE" \
    -e INPUT_DRY_RUN="false" \
    repo-file-sync-action

echo ""
echo "✅ Action completed successfully!"
echo ""

# Display outputs
if [[ -f "$GITHUB_OUTPUT" ]]; then
    echo "📊 Action outputs:"
    cat "$GITHUB_OUTPUT"
    echo ""
fi

# Show synced files
echo "📂 Synced files in $OUTPUT_DIR:"
if [[ -d "$OUTPUT_DIR" ]] && [[ "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]]; then
    ls -la "$OUTPUT_DIR"
else
    echo "  (no files synced)"
fi

echo ""
echo "🎉 Local test completed! Check the $OUTPUT_DIR directory for synced files."