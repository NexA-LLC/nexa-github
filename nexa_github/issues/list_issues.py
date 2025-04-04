import os
import json
import argparse
import time
from dotenv import load_dotenv
import requests
from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportQueryError
import traceback

# 環境変数の読み込み
load_dotenv()

# GitHubのGraphQLエンドポイント
GITHUB_API_URL = 'https://api.github.com/graphql'
# GitHubのトークン
GITHUB_TOKEN = os.getenv('GITHUB_MIGRATION_TOKEN')
# キャッシュファイルのパス
CACHE_FILE = 'issues_cache.json'

# レート制限対策の設定
MAX_RETRIES = 10  # 最大リトライ回数を10回に増加
INITIAL_WAIT = 3600  # 初期待機時間（1時間）
MAX_WAIT = 21600  # 最大待機時間（6時間）
BACKOFF_FACTOR = 1.5  # 待機時間の増加倍率を緩和

# GraphQLクライアントの初期化
transport = RequestsHTTPTransport(
    url=GITHUB_API_URL,
    headers={'Authorization': f'Bearer {GITHUB_TOKEN}'}
)
client = Client(transport=transport, fetch_schema_from_transport=False)

def load_cache():
    """キャッシュからデータを読み込む"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_cache(data):
    """データをキャッシュに保存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_project_id(org_name, project_number):
    """組織のプロジェクトIDを取得"""
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    query = """
    query {
        organization(login: "%s") {
            projectV2(number: %s) {
                id
            }
        }
    }
    """ % (org_name, project_number)
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': query}
    )
    
    if response.status_code != 200:
        raise Exception(f"プロジェクトIDの取得に失敗: {response.text}")
    
    data = response.json()
    if 'errors' in data:
        raise Exception(f"プロジェクトIDの取得に失敗: {data['errors']}")
    
    return data['data']['organization']['projectV2']['id']

def get_project_item_by_id(project_id, item_id):
    """特定のアイテムを取得"""
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    query = """
    query {
        node(id: "%s") {
            ... on ProjectV2Item {
                id
                type
                content {
                    ... on DraftIssue {
                        title
                        body
                        createdAt
                        updatedAt
                    }
                    ... on Issue {
                        title
                        body
                        createdAt
                        updatedAt
                        state
                        number
                        repository {
                            name
                        }
                    }
                    ... on PullRequest {
                        title
                        body
                        createdAt
                        updatedAt
                        state
                        number
                        repository {
                            name
                        }
                    }
                }
                fieldValues(first: 20) {
                    nodes {
                        ... on ProjectV2ItemFieldTextValue {
                            field {
                                ... on ProjectV2Field {
                                    name
                                }
                            }
                            text
                        }
                        ... on ProjectV2ItemFieldDateValue {
                            field {
                                ... on ProjectV2Field {
                                    name
                                }
                            }
                            date
                        }
                        ... on ProjectV2ItemFieldSingleSelectValue {
                            field {
                                ... on ProjectV2Field {
                                    name
                                }
                            }
                                    name
                        }
                    }
                }
            }
        }
    }
    """ % item_id
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': query}
    )
    
    if response.status_code != 200:
        raise Exception(f"アイテムの取得に失敗: {response.text}")
    
    data = response.json()
    if 'errors' in data:
        raise Exception(f"アイテムの取得に失敗: {data['errors']}")
    
    return data['data']['node']

def get_project_items(project_id, force_refresh=False):
    """プロジェクトのアイテム一覧を取得（Todoステータスで、descriptionに「ステータス: Done」が含まれているもののみ）"""
    # キャッシュをチェック
    if not force_refresh:
        cached_data = load_cache()
        if cached_data:
            print("キャッシュからデータを読み込みました")
            return cached_data
    
    query = """
    query($projectId: ID!, $first: Int!, $after: String) {
        node(id: $projectId) {
            ... on ProjectV2 {
                items(first: $first, after: $after) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        status: fieldValueByName(name: "Status") {
                            ... on ProjectV2ItemFieldSingleSelectValue {
                                name
                            }
                        }
                        content {
                            ... on DraftIssue {
                                id
                                title
                                body
                                createdAt
                                updatedAt
                                __typename
                            }
                            ... on Issue {
                                id
                                number
                                title
                                body
                                issueState: state
                                createdAt
                                updatedAt
                                repository {
                                    name
                                }
                                labels(first: 10) {
                                    nodes {
                                        name
                                    }
                                }
                                assignees(first: 10) {
                                    nodes {
                                        login
                                    }
                                }
                            }
                            ... on PullRequest {
                                id
                                number
                                title
                                body
                                prState: state
                                createdAt
                                updatedAt
                                repository {
                                    name
                                }
                                labels(first: 10) {
                                    nodes {
                                        name
                                    }
                                }
                                assignees(first: 10) {
                                    nodes {
                                        login
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    all_items = []
    has_next_page = True
    after = None
    
    while has_next_page:
        try:
            variables = {
                "projectId": project_id,
                "first": 100,
                "after": after
            }
            
            result = client.execute(gql(query), variable_values=variables)
            items = result['node']['items']['nodes']
            
            # Todoステータスで、descriptionに「ステータス: Done」が含まれているアイテムのみを抽出
            filtered_items = []
            for item in items:
                content = item.get('content', {})
                if not content:
                    continue
                    
                # ステータスがTodoかチェック
                status = item.get('status', {}).get('name')
                if status != 'Todo':
                    continue
                
                # bodyに「ステータス: Done」が含まれているかチェック
                body = content.get('body', '')
                if 'ステータス: Done' not in body:
                    continue
                
                filtered_items.append(item)
                print(f"条件に合致するアイテムを追加: {content.get('title', 'タイトルなし')} (タイプ: {content.get('__typename', '不明')})")
            
            all_items.extend(filtered_items)
            
            page_info = result['node']['items']['pageInfo']
            has_next_page = page_info['hasNextPage']
            after = page_info['endCursor']
            
            print(f"現在の取得済みアイテム数: {len(all_items)}")
            
        except TransportQueryError as e:
            if 'rate limit exceeded' in str(e).lower():
                wait_with_backoff(0)
            else:
                raise e
    
    # キャッシュを保存
    save_cache(all_items)
    return all_items

def format_item(item):
    """アイテムの情報を整形"""
    if not item['content']:
        return None
        
    content = item['content']
    item_type = item.get('type', '不明')
    title = content.get('title', 'タイトルなし')
    body = content.get('body', '')
    created_at = content.get('createdAt', '')
    updated_at = content.get('updatedAt', '')
    
    # Issue/PRの場合の追加情報
    state = content.get('issueState') or content.get('prState', '')
    number = content.get('number', '')
    repository = content.get('repository', {}).get('name', '')
    
    # ステータスを取得
    status = '未設定'
    custom_fields = {}
    for field_value in item.get('fieldValues', {}).get('nodes', []):
        if isinstance(field_value, dict) and 'field' in field_value:
            field_name = field_value['field'].get('name', '')
            if field_name.lower() == 'status' and 'name' in field_value:
                status = field_value['name']
            elif 'text' in field_value:
                custom_fields[field_name] = field_value['text']
            elif 'date' in field_value:
                custom_fields[field_name] = field_value['date']
    
    # JIRAのIDを抽出
    jira_id = ''
    if body and '移行元: JIRA Issue' in body:
        jira_id = body.split('移行元: JIRA Issue')[1].split('\n')[0].strip()
    
    result = {
        'id': item.get('id', ''),
        'type': item_type,
        'title': title,
        'body': body,
        'status': status,
        'jira_id': jira_id,
        'created_at': created_at,
        'updated_at': updated_at,
        'custom_fields': custom_fields
    }
    
    # Issue/PRの場合は追加情報を含める
    if state:
        result.update({
            'state': state,
            'number': number,
            'repository': repository
        })
    
    return result

def wait_with_backoff(retry_count):
    """バックオフ戦略に基づいて待機時間を計算"""
    wait_time = min(INITIAL_WAIT * (BACKOFF_FACTOR ** retry_count), MAX_WAIT)
    hours = wait_time / 3600
    print(f"レート制限に達しました。{hours:.1f}時間待機します...")
    time.sleep(wait_time)

def handle_rate_limit_error(e, retry_count):
    """レート制限エラーの処理"""
    if 'RATE_LIMITED' in str(e):
        if retry_count < MAX_RETRIES:
            wait_with_backoff(retry_count)
            return True
        else:
            print(f"最大リトライ回数（{MAX_RETRIES}回）に達しました。処理を終了します。")
    return False

def get_status_field(project_id):
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
    
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            result = client.execute(query, variable_values={'projectId': project_id})
            status_field = result['node']['field']
            return status_field
        except TransportQueryError as e:
            if handle_rate_limit_error(e, retry_count):
                retry_count += 1
                continue
            print(f"ステータスフィールドの取得に失敗: {str(e)}")
            return None
        except Exception as e:
            print(f"予期せぬエラーが発生しました: {str(e)}")
            return None
    
    return None

def update_item_status(project_id, item_id, status_value):
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            # ステータスフィールドの取得
            status_field = get_status_field(project_id)
            if not status_field:
                print(f"ステータスフィールドが見つかりません: {item_id}")
                return False

            # "Done"オプションのIDを探す
            done_option = next((opt for opt in status_field['options'] if opt['name'] == status_value), None)
            if not done_option:
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
                'optionId': done_option['id']
            })

            print(f"ステータスを '{status_value}' に更新しました")
            return True

        except TransportQueryError as e:
            if handle_rate_limit_error(e, retry_count):
                retry_count += 1
                continue
            print(f"ステータスの更新に失敗: {str(e)}")
            return False
        except Exception as e:
            print(f"予期せぬエラーが発生しました: {str(e)}")
            return False
    
    return False

def print_item(item):
    """アイテムの情報を表示"""
    content = item.get('content', {})
    if not content:
        return
    
    print(f"ID: {item.get('id', 'N/A')}")
    print(f"タイトル: {content.get('title', 'タイトルなし')}")
    
    status = None
    if item.get('status'):
        status = item['status'].get('name')
    print(f"ステータス: {status or '未設定'}")
    
    if content.get('repository'):
        print(f"リポジトリ: {content['repository'].get('name', 'N/A')}")
        print(f"番号: #{content.get('number', 'N/A')}")
    
    print(f"作成日: {content.get('createdAt', 'N/A')}")
    print(f"更新日: {content.get('updatedAt', 'N/A')}")
    
    print("\n本文:")
    print(content.get('body', '(本文なし)'))
    print("-" * 50)

def convert_draft_to_issue(project_id, draft_id, repository_id):
    """DraftIssueをIssueに変換"""
    mutation = gql("""
    mutation($projectId: ID!, $draftId: ID!, $repositoryId: ID!) {
        convertProjectDraftIssueToIssue(
            input: {
                projectId: $projectId
                draftId: $draftId
                repositoryId: $repositoryId
            }
        ) {
            issue {
                id
                number
                title
                body
                state
            }
        }
    }
    """)
    
    try:
        result = client.execute(mutation, variable_values={
            'projectId': project_id,
            'draftId': draft_id,
            'repositoryId': repository_id
        })
        return result['convertProjectDraftIssueToIssue']['issue']
    except Exception as e:
        print(f"DraftIssueの変換に失敗: {str(e)}")
        return None

def get_repository_id(org_name, repo_name):
    """リポジトリIDを取得"""
    query = gql("""
    query($org: String!, $repo: String!) {
        repository(owner: $org, name: $repo) {
            id
        }
    }
    """)
    
    try:
        result = client.execute(query, variable_values={
            'org': org_name,
            'repo': repo_name
        })
        return result['repository']['id']
    except Exception as e:
        print(f"リポジトリIDの取得に失敗: {str(e)}")
        return None

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='GitHubプロジェクトのアイテム一覧を取得')
    parser.add_argument('--refresh', action='store_true', help='キャッシュを無視して最新のデータを取得')
    parser.add_argument('--convert-drafts', action='store_true', help='DraftIssueをIssueに変換')
    args = parser.parse_args()

    try:
        # プロジェクトIDを取得
        project_id = get_project_id('NexA-LLC', 2)
        print(f"プロジェクトID: {project_id}")

        # アイテム一覧を取得
        items = get_project_items(project_id, args.refresh)
        print(f"\n{len(items)}件のアイテムが見つかりました\n")

        # DraftIssueの変換
        if args.convert_drafts:
            repo_id = get_repository_id('NexA-LLC', 'unity-sabong-client')
            if not repo_id:
                print("リポジトリIDの取得に失敗しました")
                return

            for item in items:
                content = item.get('content', {})
                if not content:
                    continue

                # DraftIssueの場合のみ変換
                if content.get('__typename') == 'DraftIssue':
                    print(f"DraftIssueを変換中: {content.get('title', 'タイトルなし')}")
                    converted_issue = convert_draft_to_issue(project_id, content['id'], repo_id)
                    if converted_issue:
                        print(f"変換成功: #{converted_issue['number']} {converted_issue['title']}")
                    else:
                        print("変換に失敗しました")

        # 各アイテムのステータスを更新
        for item in items:
            print_item(item)
            try:
                update_item_status(project_id, item['id'], 'Done')
                print(f"ステータスをDoneに更新しました: {item['content']['title']}")
            except Exception as e:
                print(f"ステータスの更新に失敗しました: {str(e)}")
                continue

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        print(f"スタックトレース: {traceback.format_exc()}")

if __name__ == '__main__':
    main() 