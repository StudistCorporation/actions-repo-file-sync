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
CREATE_PR=""
PR_TITLE=""
PR_BODY=""
BRANCH_NAME=""

# Set flags based on input parameters
if [[ "${INPUT_DRY_RUN:-false}" == "true" ]]; then
    DRY_RUN="--dry-run"
fi

if [[ "${INPUT_CREATE_PR:-false}" == "true" ]]; then
    CREATE_PR="--create-pr"
fi

if [[ -n "${INPUT_PR_TITLE:-}" ]]; then
    PR_TITLE="--pr-title"
fi

if [[ -n "${INPUT_PR_BODY:-}" ]]; then
    PR_BODY="--pr-body"
fi

if [[ -n "${INPUT_BRANCH_NAME:-}" ]]; then
    BRANCH_NAME="--branch-name"
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
        --create-pr)
            CREATE_PR="--create-pr"
            shift
            ;;
        --pr-title)
            PR_TITLE="--pr-title"
            shift 2
            ;;
        --pr-body)
            PR_BODY="--pr-body"
            shift 2
            ;;
        --branch-name)
            BRANCH_NAME="--branch-name"
            shift 2
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
log "DEBUG: INPUT_CREATE_PR=${INPUT_CREATE_PR:-NOT_SET}"
log "DEBUG: INPUT_DRY_RUN=${INPUT_DRY_RUN:-NOT_SET}"
log "DEBUG: CREATE_PR flag=${CREATE_PR}"

# Check if config file exists
if [[ ! -f "${CONFIG_FILE}" ]]; then
    log "Error: Configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Build command
CMD=(uv run python -m src.cli)
CMD+=("--config" "${CONFIG_FILE}")
CMD+=("--output" "${OUTPUT_DIR}")

if [[ -n "${DRY_RUN}" ]]; then
    CMD+=("${DRY_RUN}")
fi

if [[ -n "${CREATE_PR}" ]]; then
    CMD+=("${CREATE_PR}")
fi

if [[ -n "${PR_TITLE}" && -n "${INPUT_PR_TITLE:-}" ]]; then
    CMD+=("${PR_TITLE}" "${INPUT_PR_TITLE}")
fi

if [[ -n "${PR_BODY}" && -n "${INPUT_PR_BODY:-}" ]]; then
    CMD+=("${PR_BODY}" "${INPUT_PR_BODY}")
fi

if [[ -n "${BRANCH_NAME}" && -n "${INPUT_BRANCH_NAME:-}" ]]; then
    CMD+=("${BRANCH_NAME}" "${INPUT_BRANCH_NAME}")
fi

# Run the sync command and capture output
log "Executing: ${CMD[*]}"

# Capture stdout and stderr
if output=$("${CMD[@]}" 2>&1); then
    
    log "Sync completed successfully"
    exit_code=0
else
    exit_code=$?
    log "Sync failed with exit code: ${exit_code}"
    echo "${output}"
    exit ${exit_code}
fi

# Extract synced files from output
files_synced=""

# Parse sync results to extract repo:file pairs
# Look for lines like "✓ Downloaded owner/repo:ref:file -> path" (normal mode)
# or "Would download owner/repo:ref:file" (dry-run mode)
while IFS= read -r line; do
    if [[ "${line}" =~ ✓\ Downloaded\ ([^:]+):([^:]+):([^\ ]+) ]]; then
        # Normal mode: actual download
        repo="${BASH_REMATCH[1]}"
        file="${BASH_REMATCH[3]}"
        if [[ -n "${files_synced}" ]]; then
            files_synced="${files_synced},${repo}:${file}"
        else
            files_synced="${repo}:${file}"
        fi
    elif [[ "${line}" =~ Would\ download\ ([^:]+):([^:]+):([^\ ]+) ]]; then
        # Dry-run mode: would download
        repo="${BASH_REMATCH[1]}"
        file="${BASH_REMATCH[3]}"
        if [[ -n "${files_synced}" ]]; then
            files_synced="${files_synced},${repo}:${file}"
        else
            files_synced="${repo}:${file}"
        fi
    fi
done <<< "${output}"

# Set GitHub Actions output
github_output "files-synced" "${files_synced}"

log "Files synced: ${files_synced}"

# Show the actual output
echo "${output}"

log "repo-file-sync GitHub Action completed successfully"