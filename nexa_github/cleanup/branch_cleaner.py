#!/usr/bin/env python3
import os
import sys
import json
import argparse
from typing import Optional
from nexa_github import GitHubManager

def cleanup_branches(input_file: str = 'devin_branches.json', days: int = 4, dry_run: bool = True) -> None:
    """Cleanup old Devin branches"""
    if not os.path.exists(input_file):
        print(f"エラー: {input_file} が見つかりません")
        print("先に list-repos コマンドを実行してください")
        sys.exit(1)

    try:
        gh = GitHubManager()
        
        with open(input_file, 'r', encoding='utf-8') as f:
            repos_info = json.load(f)
        
        print(f"{len(repos_info)}個のリポジトリの処理を開始します\n")
        
        for repo in repos_info:
            print(f"\nリポジトリ {repo['full_name']} の処理中...")
            for branch in repo['devin_branches']:
                result = gh.delete_old_branch(
                    repo['full_name'],
                    branch,
                    days_old=days,
                    dry_run=dry_run
                )
                
                status_emoji = {
                    'skipped': '⏭️',
                    'simulation': '🔍',
                    'deleted': '✅',
                    'error': '❌'
                }.get(result['status'], '❓')
                
                print(f"{status_emoji} {result['branch']}: {result['message']}")
                
    except Exception as e:
        print(f"エラー: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='GitHub Branch Cleaner')
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # list-repos コマンド
    list_parser = subparsers.add_parser('list-repos', help='全てのアクセス可能なリポジトリを一覧表示')
    list_parser.add_argument('--output', '-o', default=None,
                            help='出力JSONファイル名（オプション）')
    
    # cleanup コマンド
    cleanup_parser = subparsers.add_parser('cleanup', help='古いDevinブランチを削除')
    cleanup_parser.add_argument('--input', '-i', default='devin_branches.json',
                               help='入力JSONファイル名 (デフォルト: devin_branches.json)')
    cleanup_parser.add_argument('--days', '-d', type=int, default=4,
                               help='この日数より古いブランチを削除 (デフォルト: 4)')
    cleanup_parser.add_argument('--execute', '-e', action='store_true',
                               help='実際に削除を実行（指定しない場合はシミュレーションのみ）')
    
    args = parser.parse_args()
    
    if args.command == 'list-repos':
        gh = GitHubManager()
        gh.list_repos_cmd(args.output)
    elif args.command == 'cleanup':
        cleanup_branches(args.input, args.days, not args.execute)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main() 