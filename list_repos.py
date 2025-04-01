import os
import json
from dotenv import load_dotenv
import requests
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# 環境変数の読み込み
load_dotenv()

# GitHubのGraphQLエンドポイント
GITHUB_API_URL = 'https://api.github.com/graphql'
# GitHubのトークン
GITHUB_TOKEN = os.getenv('GITHUB_MIGRATION_TOKEN')

# GraphQLクライアントの初期化
transport = RequestsHTTPTransport(
    url=GITHUB_API_URL,
    headers={'Authorization': f'Bearer {GITHUB_TOKEN}'}
)
client = Client(transport=transport, fetch_schema_from_transport=False)

def get_accessible_repositories():
    """アクセス可能なリポジトリの一覧を取得（個人と組織の両方）"""
    query = """
    query($first: Int!, $after: String) {
        viewer {
            repositories(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    name
                    owner {
                        login
                        __typename
                    }
                    description
                    visibility
                    isPrivate
                    isArchived
                    isFork
                    defaultBranchRef {
                        name
                    }
                    updatedAt
                }
            }
            organizations(first: 100) {
                nodes {
                    name
                    repositories(first: $first, after: $after) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            name
                            owner {
                                login
                                __typename
                            }
                            description
                            visibility
                            isPrivate
                            isArchived
                            isFork
                            defaultBranchRef {
                                name
                            }
                            updatedAt
                        }
                    }
                }
            }
        }
    }
    """
    
    try:
        all_repos = []
        has_next_page = True
        end_cursor = None
        
        while has_next_page:
            result = client.execute(gql(query), variable_values={
                'first': 100,
                'after': end_cursor
            })
            
            # 個人のリポジトリを追加
            viewer_repos = result['viewer']['repositories']
            all_repos.extend(viewer_repos['nodes'])
            
            # 組織のリポジトリを追加
            for org in result['viewer']['organizations']['nodes']:
                org_repos = org['repositories']
                all_repos.extend(org_repos['nodes'])
            
            # ページネーション情報を更新
            has_next_page = viewer_repos['pageInfo']['hasNextPage']
            end_cursor = viewer_repos['pageInfo']['endCursor']
            
            print(f"取得済みリポジトリ数: {len(all_repos)}")
        
        return all_repos
    except Exception as e:
        print(f'リポジトリ一覧の取得に失敗しました: {str(e)}')
        return []

def print_repo(repo):
    """リポジトリの情報を表示"""
    owner_type = repo['owner']['__typename']
    print(f"リポジトリ名: {repo['owner']['login']}/{repo['name']}")
    print(f"オーナータイプ: {owner_type}")
    print(f"説明: {repo['description'] or 'なし'}")
    print(f"可視性: {repo['visibility']}")
    print(f"プライベート: {'はい' if repo['isPrivate'] else 'いいえ'}")
    print(f"アーカイブ済み: {'はい' if repo['isArchived'] else 'いいえ'}")
    print(f"フォーク: {'はい' if repo['isFork'] else 'いいえ'}")
    print(f"デフォルトブランチ: {repo['defaultBranchRef']['name'] if repo['defaultBranchRef'] else 'なし'}")
    print(f"最終更新: {repo['updatedAt']}")
    print("-" * 50)

def main():
    """メイン処理"""
    print("アクセス可能なリポジトリの一覧を取得中...")
    repos = get_accessible_repositories()
    
    if not repos:
        print("リポジトリが見つかりませんでした。")
        return
    
    print(f"\n合計 {len(repos)} 件のリポジトリが見つかりました\n")
    
    # リポジトリの情報を表示
    for repo in repos:
        print_repo(repo)
    
    # 結果をJSONファイルに保存
    with open('repos.json', 'w', encoding='utf-8') as f:
        json.dump(repos, f, ensure_ascii=False, indent=2)
    print("\nリポジトリ情報を repos.json に保存しました")

if __name__ == '__main__':
    main() 