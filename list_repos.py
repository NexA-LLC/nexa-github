#!/usr/bin/env python3
import json
import sys
from github_utils import GitHubManager

def main():
    try:
        # GitHubマネージャーの初期化
        gh = GitHubManager()
        
        # リポジトリとDevinブランチの情報を取得
        print("リポジトリを検索中...")
        repos_info = gh.get_repos_with_devin_branches()
        
        if not repos_info:
            print("Devinブランチを含むリポジトリが見つかりませんでした")
            return
        
        # 結果を表示
        print(f"\n{len(repos_info)}個のリポジトリにDevinブランチが見つかりました:\n")
        
        # 結果をJSONファイルに保存
        output_file = 'devin_branches.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(repos_info, f, indent=2, ensure_ascii=False)
        
        # 結果を画面に表示
        for repo in repos_info:
            print(f"\nリポジトリ: {repo['full_name']}")
            for branch in repo['devin_branches']:
                print(f"  - {branch['name']} (最終更新: {branch['last_commit_date']})")
        
        print(f"\n詳細な情報は {output_file} に保存されました")
        
    except ValueError as e:
        print(f"エラー: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 