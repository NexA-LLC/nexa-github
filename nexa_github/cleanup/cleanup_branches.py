#!/usr/bin/env python3
import os
import sys
import json
from nexa_github.github_utils import GitHubManager

def main():
    # 入力ファイルの確認
    input_file = 'devin_branches.json'
    if not os.path.exists(input_file):
        print(f"エラー: {input_file} が見つかりません")
        print("先に list_repos.py を実行してください")
        sys.exit(1)

    try:
        # GitHubマネージャーの初期化
        gh = GitHubManager()
        
        # JSONファイルの読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            repos_info = json.load(f)
        
        print(f"{len(repos_info)}個のリポジトリの処理を開始します\n")
        
        # 各リポジトリとブランチの処理
        for repo in repos_info:
            print(f"\nリポジトリ {repo['full_name']} の処理中...")
            for branch in repo['devin_branches']:
                result = gh.delete_old_branch(
                    repo['full_name'],
                    branch,
                    days_old=4,
                    dry_run=True  # シミュレーションモード
                )
                
                # 結果の表示
                status_emoji = {
                    'skipped': '⏭️',
                    'simulation': '🔍',
                    'deleted': '✅',
                    'error': '❌'
                }.get(result['status'], '❓')
                
                print(f"{status_emoji} {result['branch']}: {result['message']}")
                
    except ValueError as e:
        print(f"エラー: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 