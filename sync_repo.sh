#!/bin/bash

# 引数チェック
if [ $# -ne 1 ]; then
    echo "使用方法: $0 <リポジトリ名>"
    echo "例: $0 webapp-mangasensei"
    exit 1
fi

REPO_NAME=$1

# GitHubとBitbucketのURLを設定
GITHUB_URL="git@github.com:NexA-LLC/${REPO_NAME}.git"
BITBUCKET_URL="git@bitbucket.org:nex-a/${REPO_NAME}.git"

echo "リポジトリ ${REPO_NAME} の同期を開始します..."

# リポジトリのクローン
echo "GitHubからクローン中..."
git clone ${GITHUB_URL}

# クローンしたディレクトリに移動
cd ${REPO_NAME}

# upstreamの追加
echo "upstreamの追加中..."
git remote add upstream ${BITBUCKET_URL}

# upstreamからのフェッチ
echo "upstreamからのフェッチ中..."
git fetch upstream

# Git LFSのフェッチ
echo "Git LFSのフェッチ中..."
git lfs fetch --all

# upstream-mainブランチの作成とトラッキング
echo "upstream-mainブランチの作成中..."
if git show-ref --verify --quiet refs/remotes/upstream/main; then
    git checkout -b upstream-main --track upstream/main
else
    echo "警告: upstreamのmainブランチが見つかりません。空のリポジトリの可能性があります。"
    git checkout -b upstream-main
fi

# ステータス確認
echo "現在のステータス:"
git status

# mainブランチの存在確認と作成
echo "mainブランチの確認中..."
if ! git show-ref --verify --quiet refs/heads/main; then
    echo "mainブランチが存在しないため、作成します..."
    git checkout -b main
else
    echo "mainブランチが存在するため、切り替えます..."
    git checkout main
fi

# upstream-mainの内容をmainにマージ
echo "upstream-mainの内容をmainにマージ中..."
if git show-ref --verify --quiet refs/heads/upstream-main; then
    git merge upstream-main
else
    echo "警告: upstream-mainブランチが見つかりません。スキップします。"
fi

# 初期コミットの作成（必要な場合）
if [ -z "$(git status --porcelain)" ]; then
    echo "空のリポジトリのため、初期コミットを作成します..."
    echo "# ${REPO_NAME}" > README.md
    git add README.md
    git commit -m "Initial commit"
fi

# mainブランチへのプッシュ
echo "mainブランチへのプッシュ中..."
git push -u origin main

echo "同期が完了しました！" 