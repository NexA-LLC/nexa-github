# nexa_github

GitHubリポジトリ管理用のPythonパッケージです。

## 機能

- リポジトリ一覧の取得と表示
- Devinブランチの管理（古いブランチの自動クリーンアップ）

## インストール

```bash
pip install -e .
```

## 環境変数

以下の環境変数が必要です：

- `GITHUB_TOKEN`: GitHubのアクセストークン

## 使用方法

### コマンドライン

#### リポジトリ一覧の表示

```bash
# 全てのアクセス可能なリポジトリを表示
github-branch-cleaner list-repos

# JSONファイルに出力
github-branch-cleaner list-repos --output repos.json
```

#### Devinブランチのクリーンアップ

```bash
# シミュレーションモード（実際の削除は行わない）
github-branch-cleaner cleanup

# 実際に削除を実行
github-branch-cleaner cleanup --execute

# カスタム設定でクリーンアップ
github-branch-cleaner cleanup --days 7 --input custom.json --execute
```

### Pythonコード内での使用

```python
from nexa_github import GitHubManager

# GitHubManagerのインスタンス化
gh = GitHubManager()

# リポジトリ一覧の取得
repos = gh.list_repositories()

# Devinブランチを持つリポジトリの取得
repos_with_devin = gh.get_repos_with_devin_branches()

# 古いブランチの削除
result = gh.delete_old_branch(
    repo_full_name="owner/repo",
    branch_info={"name": "branch-name", "last_commit_date": "2024-01-01T00:00:00"},
    days_old=4,
    dry_run=True
)
```

## 開発

### 必要要件

- Python 3.8以上
- PyGithub
- python-dotenv

### テスト

```bash
# TODO: テストの実行方法を追加
```

## ライセンス

Copyright (c) NexA LLC. All rights reserved.
