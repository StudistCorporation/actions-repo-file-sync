# Repo File Sync

GitHub リポジトリから指定されたファイルを YAML 設定に基づいてローカルに同期するPythonツールです。環境変数の置換機能も提供します。

## 機能

- 複数のGitHubリポジトリから複数のファイルを一括ダウンロード
- プライベートリポジトリのサポート（GitHub token使用）
- ダウンロードしたファイル内での環境変数置換
- 外部ファイルからの環境変数定義読み込み
- ドライランモード（実際にファイルを作成せずに動作確認）
- ディレクトリ構造の保持オプション
- 接続テスト機能

## インストール

```bash
# 依存関係のインストール
uv sync

# 開発用依存関係も含める場合
uv sync --group dev
```

## 設定

### 1. メイン設定ファイル（`.github/repo-file-sync.yaml`）

```yaml
envs_file: repo-file-sync.envs.yaml
sources:
  - repo: owner/repository-name
    ref: main
    files:
    - README.md
    - LICENSE
  - repo: another-owner/another-repo
    ref: v1.0.0
    files:
    - config/settings.yaml
```

### 2. 環境変数ファイル（`repo-file-sync.envs.yaml`）

```yaml
- name: OLD_VALUE
  value: NEW_VALUE
- name: actions/checkout
  value: awesome-checkout-action
- name: PROJECT_NAME
  value: "My Awesome Project"
```

## 使い方

### GitHub Action として使用

このツールは GitHub Action として簡単に使用できます：

#### 基本的な使い方（手動コミット）

```yaml
# .github/workflows/sync-files.yml
name: Sync Repository Files

on:
  schedule:
    - cron: '0 0 * * *'  # 毎日実行
  workflow_dispatch:      # 手動実行も可能

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Sync files from other repositories
        uses: StudistCorporation/actions-repo-file-sync@main
        with:
          config: '.github/repo-file-sync.yaml'
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Commit synced files
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add ./synced-files
          git diff --staged --quiet || git commit -m "🔄 Sync files from repositories"
          git push
```

#### PR自動作成（推奨）

```yaml
# .github/workflows/sync-files-pr.yml
name: Sync Repository Files with PR

on:
  schedule:
    - cron: '0 0 * * *'  # 毎日実行
  workflow_dispatch:      # 手動実行も可能

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Sync files and create PR
        uses: StudistCorporation/actions-repo-file-sync@main
        with:
          config: '.github/repo-file-sync.yaml'
          github-token: ${{ secrets.GITHUB_TOKEN }}
          create-pr: true
          pr-title: '🔄 Sync files from repositories'
          pr-body: |
            Automated file sync from configured repositories.
            
            Files have been updated based on the latest versions from source repositories.
          branch-name: 'sync/repo-files'
```

#### 高度な使い方（カスタマイズ可能なPR作成）

```yaml
name: Advanced File Sync with Custom PR

on:
  workflow_dispatch:
    inputs:
      dry-run:
        description: 'Run in dry-run mode'
        required: false
        default: false
        type: boolean
      create-pr:
        description: 'Create pull request'
        required: false
        default: true
        type: boolean
      branch-name:
        description: 'Branch name for PR'
        required: false
        default: 'sync/repo-files'
        type: string

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Sync files with advanced options
        uses: StudistCorporation/actions-repo-file-sync@main
        with:
          config: '.github/custom-sync-config.yaml'
          github-token: ${{ secrets.PAT_TOKEN }}  # カスタムトークン
          dry-run: ${{ github.event.inputs.dry-run }}
          create-pr: ${{ github.event.inputs.create-pr }}
          pr-title: '🔄 Custom sync: ${{ github.event.inputs.branch-name }}'
          pr-body: |
            Automated file sync triggered manually.
            
            - Branch: ${{ github.event.inputs.branch-name }}
            - Dry run: ${{ github.event.inputs.dry-run }}
            - Triggered by: @${{ github.actor }}
          branch-name: ${{ github.event.inputs.branch-name }}
        id: sync

      - name: Show sync results
        run: |
          echo "Files synced: ${{ steps.sync.outputs.files-synced }}"
```

#### 入力パラメータ

| パラメータ | 説明 | 必須 | デフォルト |
|-----------|------|------|------------|
| `config` | 設定ファイルのパス | No | `.github/repo-file-sync.yaml` |
| `github-token` | GitHubトークン | No | `${{ github.token }}` |
| `dry-run` | ドライランモード | No | `false` |
| `create-pr` | プルリクエストを作成する | No | `false` |
| `pr-title` | プルリクエストのタイトル | No | `🔄 Sync files from repositories` |
| `pr-body` | プルリクエストの説明文 | No | `Automated file sync from configured repositories` |
| `branch-name` | プルリクエスト用のブランチ名 | No | `sync/repo-files` |

#### 出力パラメータ

| パラメータ | 説明 |
|-----------|------|
| `files-synced` | 同期されたファイル一覧（形式: `repo:file,repo:file`） |

### コマンドラインツールとして使用

#### 基本的な使い方

```bash
# デフォルト設定でファイルを同期
uv run python -m src.cli

# カスタム設定ファイルを使用
uv run python -m src.cli --config custom-config.yaml

# カスタム出力ディレクトリを指定
uv run python -m src.cli --output ./downloads

# 詳細ログを表示
uv run python -m src.cli --verbose
```

### プライベートリポジトリを使用する場合

```bash
# GitHub tokenを環境変数で設定
export GITHUB_TOKEN=ghp_your_token_here
uv run python -m src.cli
```

### その他のオプション

```bash
# ドライラン（実際にファイルを作成しない）
uv run python -m src.cli --dry-run

# リポジトリのディレクトリ構造を保持
uv run python -m src.cli --preserve-structure

# 接続テスト
uv run python -m src.cli --test-connection

# プルリクエストを作成
uv run python -m src.cli --create-pr

# カスタムPRタイトルとブランチ名
uv run python -m src.cli --create-pr --pr-title "Custom sync" --branch-name "feature/sync"

# タイムアウトを設定（秒）
uv run python -m src.cli --timeout 60

# ヘルプを表示
uv run python -m src.cli --help
```

## 環境変数置換

ダウンロードしたファイル内で文字列の置換が行われます：

### 置換前のファイル内容
```yaml
name: actions/checkout
version: v4
project: PROJECT_NAME
```

### 置換後のファイル内容
```yaml
name: awesome-checkout-action
version: v4
project: My Awesome Project
```

## テスト

### テストの実行

```bash
# 全テストを実行
uv run pytest

# 詳細な出力でテストを実行
uv run pytest -v

# カバレッジレポート付きでテストを実行
uv run pytest --cov=src --cov-report=term-missing

# 特定のテストファイルのみ実行
uv run pytest tests/test_config.py

# 特定のテストケースのみ実行
uv run pytest tests/test_config.py::test_load_config_with_envs_file
```

### テストの種類

#### 1. 単体テスト（Unit Tests）

- **`tests/test_config.py`** - 設定ファイルの解析とバリデーション
- **`tests/test_github.py`** - GitHubクライアントの機能
- **`tests/test_cli.py`** - コマンドライン引数の解析と実行

#### 2. 統合テスト（Integration Tests）

- **`tests/test_integration.py`** - エンドツーエンドの動作確認
  - 環境変数置換の統合テスト
  - 実際のGitHub APIとの連携テスト（`GITHUB_TOKEN`が設定されている場合）
  - ドライランモードのテスト

### テストデータ

テスト用の設定ファイルは `tests/fixtures/` ディレクトリに配置されています：

- `test-config.yaml` - テスト用メイン設定
- `test-envs.yaml` - テスト用環境変数定義

### モックとフィクスチャ

- HTTP リクエストは `responses` ライブラリでモック
- ファイルシステム操作は `tmp_path` フィクスチャを使用
- 設定ファイルの読み込みテスト用のサンプルデータを提供

### 実際のGitHub APIテスト

実際のGitHub APIを使用したテストを実行するには：

```bash
export GITHUB_TOKEN=your_github_token
uv run pytest tests/test_integration.py::TestIntegration::test_real_github_integration
```

## コード品質

### リンティング

```bash
# コードの静的解析
uv run ruff check .

# 自動修正可能な問題を修正
uv run ruff check . --fix

# コードフォーマット
uv run ruff format .
```

### 型チェック

```bash
# 型チェック（オプション、pyrightがインストールされている場合）
uv run pyright
```

## アーキテクチャ

### モジュール構成

```
src/
├── __init__.py          # パッケージ初期化
├── cli.py              # コマンドライン インターフェース
├── config.py           # 設定ファイル解析
├── github.py           # GitHub API クライアント
└── sync.py             # ファイル同期ロジック
```

### 主要クラス

- **`GitHubClient`** - GitHub からのファイルダウンロードと環境変数置換
- **`RepoFileSync`** - ファイル同期の統合処理
- **`SyncResult`** - 同期結果の管理
- **設定型** - TypedDict による型安全な設定管理

## トラブルシューティング

### よくある問題

1. **プライベートリポジトリにアクセスできない**
   - `GITHUB_TOKEN` 環境変数が設定されているか確認
   - トークンに適切な権限があるか確認

2. **設定ファイルが見つからない**
   - ファイルパスが正しいか確認
   - 相対パスの場合、実行ディレクトリを確認

3. **環境変数ファイルが見つからない**
   - `envs_file` パスがメイン設定ファイルからの相対パスで正しいか確認

4. **接続エラー**
   - `--test-connection` オプションで接続を確認
   - ネットワーク設定やプロキシ設定を確認

### デバッグ

詳細なログを出力してデバッグ：

```bash
uv run python -m src.cli --verbose
```

## ライセンス

このプロジェクトのライセンスについては、リポジトリのライセンスファイルを参照してください。