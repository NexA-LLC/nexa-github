import os
import json
import argparse
from dotenv import load_dotenv
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

def get_status_field(project_id):
    """ステータスフィールドの情報を取得"""
    query = gql("""
    query($projectId: ID!) {
        node(id: $projectId) {
            ... on ProjectV2 {
                field(name: "Status") {
                    ... on ProjectV2SingleSelectField {
                        id
                        options {
                            id
                            name
                        }
                    }
                }
            }
        }
    }
    """)
    
    try:
        result = client.execute(query, variable_values={'projectId': project_id})
        status_field = result['node']['field']
        return status_field
    except Exception as e:
        print(f"ステータスフィールドの取得に失敗: {str(e)}")
        return None

def update_item_status(project_id, item_id, status_value):
    """アイテムのステータスを更新"""
    try:
        # ステータスフィールドの取得
        status_field = get_status_field(project_id)
        if not status_field:
            print(f"ステータスフィールドが見つかりません: {item_id}")
            return False

        # 指定されたステータス値のオプションIDを探す
        status_option = next((opt for opt in status_field['options'] if opt['name'] == status_value), None)
        if not status_option:
            print(f"ステータス '{status_value}' のオプションが見つかりません: {item_id}")
            return False

        # ステータスの更新
        mutation = gql("""
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
            updateProjectV2ItemFieldValue(
                input: {
                    projectId: $projectId
                    itemId: $itemId
                    fieldId: $fieldId
                    value: { 
                        singleSelectOptionId: $optionId
                    }
                }
            ) {
                projectV2Item {
                    id
                }
            }
        }
        """)

        result = client.execute(mutation, variable_values={
            'projectId': project_id,
            'itemId': item_id,
            'fieldId': status_field['id'],
            'optionId': status_option['id']
        })

        return True

    except Exception as e:
        print(f"ステータスの更新に失敗: {str(e)}")
        return False

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='GitHubプロジェクトのアイテムのステータスを更新')
    parser.add_argument('--status', required=True, help='更新後のステータス値')
    parser.add_argument('--batch-size', type=int, default=10, help='一度に更新するアイテム数')
    parser.add_argument('--delay', type=float, default=1.0, help='更新間隔（秒）')
    args = parser.parse_args()
    
    # プロジェクトID
    project_id = 'PVT_kwDOC4FkRc4A1G9f'
    
    try:
        # 更新対象の読み込み
        with open('update_targets.json', 'r', encoding='utf-8') as f:
            targets = json.load(f)
        
        print(f"{len(targets)}件のアイテムを更新します...")
        
        # バッチ処理
        success_count = 0
        for i, target in enumerate(targets):
            # ステータスの更新
            if update_item_status(project_id, target['id'], args.status):
                success_count += 1
                print(f"更新成功 ({success_count}/{len(targets)}): {target['title']}")
            else:
                print(f"更新失敗: {target['title']}")
            
            # バッチサイズごとに待機
            if (i + 1) % args.batch_size == 0:
                print(f"\n{args.delay}秒待機中...")
                import time
                time.sleep(args.delay)
        
        print(f"\n更新完了: {success_count}/{len(targets)}件のアイテムを更新しました")
        
    except FileNotFoundError:
        print("update_targets.json が見つかりません")
        print("先に list_issues.py を実行して更新対象を特定してください")
        exit(1)
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        exit(1)

if __name__ == '__main__':
    main() 