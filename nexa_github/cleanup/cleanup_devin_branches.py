#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from github import Github
from typing import List, Dict

def get_repos(g: Github) -> List[Dict]:
    """Get all repositories the token has access to"""
    repos = []
    for repo in g.get_user().get_repos():
        repos.append({
            'name': repo.name,
            'full_name': repo.full_name,
            'repo_obj': repo
        })
    return repos

def cleanup_old_devin_branches(repo, days_old: int = 4) -> None:
    """Delete Devin branches older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    try:
        branches = repo.get_branches()
        for branch in branches:
            if not branch.name.startswith('devin/'):
                continue
                
            # Get the last commit date
            commit = branch.commit
            commit_date = commit.commit.author.date
            
            if commit_date < cutoff_date:
                print(f"削除予定: {repo.full_name} - {branch.name} (最終更新: {commit_date})")
                try:
                    ref = repo.get_git_ref(f"heads/{branch.name}")
                    ref.delete()
                    print(f"✓ 削除完了: {branch.name}")
                except Exception as e:
                    print(f"× 削除失敗: {branch.name} - エラー: {str(e)}")

    except Exception as e:
        print(f"リポジトリ {repo.full_name} の処理中にエラーが発生: {str(e)}")

def main():
    # GitHub トークンの取得
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("環境変数 GITHUB_TOKEN が設定されていません")
        sys.exit(1)

    # GitHub クライアントの初期化
    g = Github(github_token)
    
    # リポジトリの取得
    print("リポジトリを検索中...")
    repos = get_repos(g)
    
    if not repos:
        print("アクセス可能なリポジトリが見つかりませんでした")
        return
        
    print(f"\n{len(repos)}個のリポジトリが見つかりました\n")
    
    # 各リポジトリの古いDevinブランチを削除
    for repo_info in repos:
        print(f"\nリポジトリ {repo_info['full_name']} を処理中...")
        cleanup_old_devin_branches(repo_info['repo_obj'])

if __name__ == "__main__":
    main() 