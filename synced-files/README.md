# Repo File Sync Test

## Test Strings for Environment Variable Substitution

Basic test cases:
- Repository: awesome-checkout-action
- Version: Super Checkout V10
- External: from-external-filexxx
- Project: Awesome Project

JSON example: {"repo": "awesome-checkout-action", "version": "Super Checkout V10"}

Multiple references:
1. awesome-checkout-action
2. awesome-checkout-action
3. https://github.com/awesome-checkout-action

Edge cases:
- Start: awesome-checkout-action test
- End: test awesome-checkout-action
- Quoted: "awesome-checkout-action"