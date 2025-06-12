# Repo File Sync Test

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