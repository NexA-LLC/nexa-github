#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from github import Github

class GitHubManager:
    def __init__(self, token: str = None):
        """Initialize GitHub manager with token"""
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub トークンが設定されていません")
        self.client = Github(self.token)

    def list_repositories(self) -> List[Dict]:
        """Get all accessible repositories"""
        repos = []
        for repo in self.client.get_user().get_repos():
            repos.append({
                'name': repo.name,
                'full_name': repo.full_name,
            })
        return repos

    def list_repos_cmd(self, output_file: Optional[str] = None) -> None:
        """Command line function to list all accessible repositories"""
        try:
            print("リポジトリを検索中...")
            repos = self.list_repositories()
            
            if not repos:
                print("アクセス可能なリポジトリが見つかりませんでした")
                return
            
            print(f"\n{len(repos)}個のリポジトリが見つかりました:\n")
            
            for repo in repos:
                print(f"- {repo['full_name']}")
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(repos, f, indent=2, ensure_ascii=False)
                print(f"\n詳細な情報は {output_file} に保存されました")
                
        except Exception as e:
            print(f"エラー: {str(e)}")
            sys.exit(1)

    def get_repos_with_devin_branches(self) -> List[Dict]:
        """Get all repositories with Devin branches and their information"""
        repos_info = []
        
        for repo in self.client.get_user().get_repos():
            devin_branches = []
            try:
                branches = repo.get_branches()
                for branch in branches:
                    if branch.name.startswith('devin/'):
                        commit = branch.commit
                        commit_date = commit.commit.author.date
                        devin_branches.append({
                            'name': branch.name,
                            'last_commit_date': commit_date.isoformat(),
                            'commit_sha': commit.sha
                        })
                
                if devin_branches:  # Only add repos that have Devin branches
                    repos_info.append({
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'devin_branches': devin_branches
                    })
                    
            except Exception as e:
                print(f"リポジトリ {repo.full_name} の処理中にエラーが発生: {str(e)}")
                continue

        return repos_info

    def delete_old_branch(self, repo_full_name: str, branch_info: dict, days_old: int = 4, dry_run: bool = True) -> Dict:
        """Delete a specific branch if it's older than the specified days"""
        result = {
            'repo': repo_full_name,
            'branch': branch_info['name'],
            'status': 'unknown',
            'message': ''
        }
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        last_commit_date = datetime.fromisoformat(branch_info['last_commit_date'])
        
        if last_commit_date >= cutoff_date:
            result.update({
                'status': 'skipped',
                'message': '最終更新が新しい'
            })
            return result
            
        try:
            repo = self.client.get_repo(repo_full_name)
            ref = repo.get_git_ref(f"heads/{branch_info['name']}")
            
            if not dry_run:
                ref.delete()
                result.update({
                    'status': 'deleted',
                    'message': '削除完了'
                })
            else:
                result.update({
                    'status': 'simulation',
                    'message': '削除シミュレーション完了'
                })
                
        except Exception as e:
            result.update({
                'status': 'error',
                'message': str(e)
            })
            
        return result 