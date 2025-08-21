# Repo File Sync Test

## Test Strings for Environment Variable Substitution

Basic test cases:
- Repository: awesome-checkout-action
- Version: Super Checkout V6
- External: from-external-file
- Project: PROJECT_NAME

JSON example: {"repo": "awesome-checkout-action", "version": "Super Checkout V6"}

Multiple references:
1. awesome-checkout-action
2. awesome-checkout-action
3. https://github.com/awesome-checkout-action

Edge cases:
- Start: awesome-checkout-action test
- End: test awesome-checkout-action
- Quoted: "awesome-checkout-action"