#!/bin/bash
set -euo pipefail

# GitHub Actions entrypoint script for repo-file-sync

# Function to output GitHub Actions format
github_output() {
    local name="$1"
    local value="$2"
    echo "${name}=${value}" >> "${GITHUB_OUTPUT:-/dev/null}"
}

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Parse arguments from environment variables (GitHub Actions) or command line
CONFIG_FILE="${INPUT_CONFIG:-.github/repo-file-sync.yaml}"
OUTPUT_DIR="./synced-files"  # Fixed output directory
DRY_RUN=""

# Set flags based on input parameters
if [[ "${INPUT_DRY_RUN:-false}" == "true" ]]; then
    DRY_RUN="--dry-run"
fi

# Override with command line arguments if provided
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        *)
            # Skip empty arguments
            if [[ -n "$1" ]]; then
                log "Unknown option: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

log "Starting repo-file-sync GitHub Action"
log "Config file: ${CONFIG_FILE}"
log "Output directory: ${OUTPUT_DIR}"
log "GitHub token: ${GITHUB_TOKEN:+[REDACTED]}"

# Check if config file exists
if [[ ! -f "${CONFIG_FILE}" ]]; then
    log "Error: Configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Build command
CMD=(python -m src.cli)
CMD+=("--config" "${CONFIG_FILE}")
CMD+=("--output" "${OUTPUT_DIR}")

if [[ -n "${DRY_RUN}" ]]; then
    CMD+=("${DRY_RUN}")
fi

# Run the sync command and capture output
log "Executing: ${CMD[*]}"

# Capture stdout and stderr
if output=$(python -m src.cli \
    --config "${CONFIG_FILE}" \
    --output "${OUTPUT_DIR}" \
    ${DRY_RUN} 2>&1); then
    
    log "Sync completed successfully"
    exit_code=0
else
    exit_code=$?
    log "Sync failed with exit code: ${exit_code}"
    echo "${output}"
    exit ${exit_code}
fi

# Extract metrics from output (if available)
files_synced=0
files_failed=0
total_bytes=0

# Try to parse sync results from the output
if [[ "${output}" =~ ([0-9]+)\ successful ]]; then
    files_synced="${BASH_REMATCH[1]}"
fi

if [[ "${output}" =~ ([0-9]+)\ failed ]]; then
    files_failed="${BASH_REMATCH[1]}"
fi

if [[ "${output}" =~ ([0-9]+)\ bytes ]]; then
    total_bytes="${BASH_REMATCH[1]}"
fi

# Set GitHub Actions outputs
github_output "files-synced" "${files_synced}"
github_output "files-failed" "${files_failed}"
github_output "total-bytes" "${total_bytes}"

log "Files synced: ${files_synced}"
log "Files failed: ${files_failed}"
log "Total bytes: ${total_bytes}"

# Show the actual output
echo "${output}"

log "repo-file-sync GitHub Action completed successfully"