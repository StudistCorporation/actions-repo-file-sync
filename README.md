# Repo File Sync

This action will synchronizes files from the specified repository and creates a Pull Request with generated GitHub App token.

## Architecture

This action synchronizes files from the source repository to the repository where using that.  

```mermaid
graph LR

R[Repo]
SR1[Source Repo#1]
SR2[Source Repo#2]

SR1 --> R
SR2 --> R
```

## Usage

Create `.github/repo-file-sync.yaml`.

```yaml
# .github/repo-file-sync.yaml
StudistCorporation/common:
- .github/workflows/labeler.yaml
- .github/ISSUE_TEMPLATE/
StudistCorporation/k8s-common:
- aqua.yaml
```

And create workflow.

```yaml
# .github/workflows/repo-file-sync.yaml
steps:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Generate token
        id: generate_token
        uses: tibdex/github-app-token@v1
        with:
          app_id: ${{ secrets.APP_ID }}
          private_key: ${{ secrets.PRIVATE_KEY }}

      - name: Sync files
        uses: ./.github/actions/sync-files
        with:
          token: ${{ steps.generate_token.outputs.token }}
          username: john
          email: john@example.com
```

## Inputs

### token

The token to used for authenticating with Terraform Cloud.

### username

The username to use in the git commit.

### email

The email to use in the git commit.
