import os
import time
import argparse
import tempfile
from dotenv import load_dotenv
from jira import JIRA
from github import Github
import requests
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

# デバッグ用：環境変数の値を表示
print("=== 環境変数の値 ===")
print(f"GITHUB_MIGRATION_TOKEN: {os.getenv('GITHUB_MIGRATION_TOKEN')}")
print(f"GITHUB_PROJECT_NUMBER: {os.getenv('GITHUB_PROJECT_NUMBER')}")
print(f"JIRA_URL: {os.getenv('JIRA_URL')}")
print(f"JIRA_USERNAME: {os.getenv('JIRA_USERNAME')}")
print(f"JIRA_API_TOKEN: {os.getenv('JIRA_API_TOKEN')}")
print("==================")

# コマンドライン引数の設定
parser = argparse.ArgumentParser(description='JIRAからGitHubへのチケット移行ツール')
parser.add_argument('project_name', help='移行するJIRAプロジェクト名')
parser.add_argument('--order-by', default='created DESC', help='ソート順 (デフォルト: created DESC)')
args = parser.parse_args()

# GitHubクライアントの初期化
github = Github(os.getenv('GITHUB_MIGRATION_TOKEN'))

# JIRAクライアントの初期化
jira = JIRA(
    server=os.getenv('JIRA_URL'),
    basic_auth=(os.getenv('JIRA_USERNAME'), os.getenv('JIRA_API_TOKEN'))
)

def download_attachment(attachment):
    """添付ファイルをダウンロード"""
    response = requests.get(
        attachment.content,
        auth=(os.getenv('JIRA_USERNAME'), os.getenv('JIRA_API_TOKEN'))
    )
    return response.content

def escape_string(s):
    """GraphQLの文字列をエスケープ"""
    if s is None:
        return ""
    return str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

def create_project_item(project_id, title, body):
    """新しいGitHub Projects Beta APIを使用してアイテムを作成"""
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # プロジェクトアイテムを作成するGraphQLミューテーション
    mutation = """
    mutation {
        addProjectV2DraftIssue(input: {projectId: "%s", title: "%s", body: "%s"}) {
            projectItem {
                id
            }
        }
    }
    """ % (project_id, escape_string(title), escape_string(body))
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': mutation}
    )
    
    if response.status_code != 200:
        raise Exception(f"プロジェクトアイテムの作成に失敗: {response.text}")
    
    data = response.json()
    if 'errors' in data:
        raise Exception(f"プロジェクトアイテムの作成に失敗: {data['errors']}")
    
    return data

def get_status_field_id(project_id):
    """プロジェクトのステータスフィールドIDを取得"""
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    query = """
    query {
        node(id: "%s") {
            ... on ProjectV2 {
                fields(first: 20) {
                    nodes {
                        ... on ProjectV2Field {
                            id
                            name
                        }
                        ... on ProjectV2SingleSelectField {
                            id
                            name
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """ % project_id
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': query}
    )
    
    if response.status_code != 200:
        raise Exception(f"ステータスフィールドの取得に失敗: {response.text}")
    
    data = response.json()
    if 'errors' in data:
        raise Exception(f"ステータスフィールドの取得に失敗: {data['errors']}")
    
    # ステータスフィールドを探す
    fields = data['data']['node']['fields']['nodes']
    status_field = next((f for f in fields if f.get('name', '').lower() == 'status'), None)
    
    if not status_field:
        raise Exception("ステータスフィールドが見つかりません")
    
    return status_field

def update_item_status(project_id, item_id, status_field, jira_status):
    """プロジェクトアイテムのステータスを更新"""
    # JIRAのステータスをGitHubのステータスにマッピング
    status_mapping = {
        # Todo系
        'Open': 'Todo',
        'Reopened': 'Todo',
        
        # In Progress系
        'In Progress': 'In Progress',
        
        # Done系
        'Done': 'Done',
        'Resolved': 'Done',
        'Closed': 'Done',
    }
    
    github_status = status_mapping.get(jira_status, 'Todo')
    status_option = next((opt for opt in status_field['options'] if opt['name'].lower() == github_status.lower()), None)
    
    if not status_option:
        print(f"警告: ステータス '{github_status}' に対応するオプションが見つかりません")
        return
    
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    mutation = """
    mutation {
        updateProjectV2ItemFieldValue(input: {
            projectId: "%s"
            itemId: "%s"
            fieldId: "%s"
            value: { singleSelectOptionId: "%s" }
        }) {
            projectV2Item {
                id
            }
        }
    }
    """ % (project_id, item_id, status_field['id'], status_option['id'])
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': mutation}
    )
    
    if response.status_code != 200:
        print(f"警告: ステータスの更新に失敗: {response.text}")
        return
    
    data = response.json()
    if 'errors' in data:
        print(f"警告: ステータスの更新に失敗: {data['errors']}")
        return

def create_github_issue(jira_issue, project_id, status_field):
    """GitHubにチケットを作成"""
    # カスタムフィールドの取得
    custom_fields = []
    for field_name, field_value in jira_issue.fields.__dict__.items():
        if field_name.startswith('customfield_'):
            try:
                field_value = getattr(jira_issue.fields, field_name)
                if field_value:
                    custom_fields.append(f"- {field_name}: {field_value}")
            except:
                continue

    # 添付ファイルの処理
    attachments_section = ""
    if hasattr(jira_issue.fields, 'attachment'):
        attachments_section = "\n## 添付ファイル\n"
        for attachment in jira_issue.fields.attachment:
            attachments_section += f"- {attachment.filename}\n"

    # コメントの処理
    comments_section = ""
    if hasattr(jira_issue.fields, 'comment'):
        comments_section = "\n## コメント\n"
        for comment in jira_issue.fields.comment.comments:
            comments_section += f"""### {comment.author.displayName} - {comment.created}
{comment.body}
"""

    # プロジェクトアイテムを作成
    title = jira_issue.fields.summary
    body = f"""## 詳細
{jira_issue.fields.description or '詳細なし'}

## メタデータ
- ステータス: {jira_issue.fields.status.name}
- 担当者: {jira_issue.fields.assignee.displayName if jira_issue.fields.assignee else '未割り当て'}
- 優先度: {jira_issue.fields.priority.name if jira_issue.fields.priority else '未設定'}
- 作成日: {jira_issue.fields.created}
- 更新日: {jira_issue.fields.updated}
- 解決日: {jira_issue.fields.resolutiondate if hasattr(jira_issue.fields, 'resolutiondate') else '未解決'}
- 解決方法: {jira_issue.fields.resolution.name if hasattr(jira_issue.fields, 'resolution') and jira_issue.fields.resolution else '未解決'}

## カスタムフィールド
{chr(10).join(custom_fields) if custom_fields else 'カスタムフィールドなし'}{attachments_section}{comments_section}

---
移行元: JIRA Issue {jira_issue.key}"""

    result = create_project_item(project_id, title, body)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] アイテムを作成しました: {result}")
    
    # ステータスを設定
    item_id = result['data']['addProjectV2DraftIssue']['projectItem']['id']
    update_item_status(project_id, item_id, status_field, jira_issue.fields.status.name)
    
    return result

def get_jira_issues():
    """JIRAのチケットを取得"""
    project_name = args.project_name
    print(f'プロジェクト "{project_name}" のチケットを取得中...')
    
    jql = f'project = "{project_name}" ORDER BY {args.order_by}'
    print(f'実行するJQL: {jql}')
    
    start_at = 0
    max_results = 100
    all_issues = []
    
    while True:
        issues = jira.search_issues(jql, startAt=start_at, maxResults=max_results)
        if not issues:
            break
            
        all_issues.extend(issues)
        if len(issues) < max_results:
            break
            
        start_at += max_results
        
    print(f'{len(all_issues)}件のチケットが見つかりました')
    return all_issues

def get_project_id(org_name, project_number):
    """組織のプロジェクトIDを取得"""
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # プロジェクトを取得するGraphQLクエリ
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

def get_existing_items(project_id):
    """プロジェクトの既存アイテムを取得"""
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_MIGRATION_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    query = """
    query {
        node(id: "%s") {
            ... on ProjectV2 {
                items(first: 100) {
                    nodes {
                        id
                        content {
                            ... on DraftIssue {
                                title
                                body
                            }
                        }
                    }
                }
            }
        }
    }
    """ % project_id
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': query}
    )
    
    if response.status_code != 200:
        raise Exception(f"既存アイテムの取得に失敗: {response.text}")
    
    data = response.json()
    if 'errors' in data:
        raise Exception(f"既存アイテムの取得に失敗: {data['errors']}")
    
    return data['data']['node']['items']['nodes']

def exponential_backoff(attempt):
    """指数バックオフによる待機時間を計算"""
    # 最大待機時間を1日（86400秒）に設定
    max_wait_time = 86400  # 24時間
    wait_time = min(1 * (2 ** attempt), max_wait_time)
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if wait_time >= 3600:  # 1時間以上の場合は時間単位で表示
        hours = wait_time / 3600
        print(f"[{current_time}] APIレート制限による待機中... {hours:.1f}時間")
    elif wait_time >= 60:  # 1分以上の場合は分単位で表示
        minutes = wait_time / 60
        print(f"[{current_time}] APIレート制限による待機中... {minutes:.1f}分")
    else:
        print(f"[{current_time}] APIレート制限による待機中... {wait_time}秒")
    
    time.sleep(wait_time)

def is_issue_already_migrated(issue, existing_items):
    """チケットが既に移行済みかどうかを判定"""
    jira_id = issue.key
    
    for item in existing_items:
        if not item['content'] or not item['content'].get('body'):
            continue
            
        # JIRAのチケットIDが本文に含まれているか確認（より厳密なチェック）
        if f"移行元: JIRA Issue {jira_id}" in item['content']['body'] or f"JIRA Issue {jira_id}" in item['content']['body']:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time}] 重複を検出: JIRA ID {jira_id} が既に移行済みです")
            return True
    
    return False

def migrate_issues():
    """メインの移行処理"""
    try:
        print(f'プロジェクト "{args.project_name}" のチケットを取得中...')
        issues = get_jira_issues()
        print(f"{len(issues)}件のチケットが見つかりました")
        
        # プロジェクトIDを取得
        github_org = os.getenv('GITHUB_OWNER')
        if not github_org:
            raise Exception("GITHUB_OWNERが設定されていません")
            
        project_id = get_project_id(
            github_org,
            int(os.getenv('GITHUB_PROJECT_NUMBER'))
        )
        print(f"プロジェクトID: {project_id}")
        
        # 既存のアイテムを取得
        existing_items = get_existing_items(project_id)
        print(f"既存のアイテム数: {len(existing_items)}")
        
        # ステータスフィールドを取得
        status_field = get_status_field_id(project_id)
        print(f"利用可能なステータス: {[opt['name'] for opt in status_field['options']]}")
        
        attempt = 0
        for issue in issues:
            try:
                if is_issue_already_migrated(issue, existing_items):
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[{current_time}] スキップ: {issue.fields.summary} (JIRA ID: {issue.key}) (既に存在します)")
                    continue
                
                create_github_issue(issue, project_id, status_field)
                attempt = 0  # 成功したらリセット
            except Exception as e:
                if "rate limit" in str(e).lower():
                    attempt += 1
                    exponential_backoff(attempt)
                    continue
                else:
                    raise e
        
        print('移行が完了しました！')
        
    except Exception as e:
        print(f'移行中にエラーが発生しました: {str(e)}')
        exit(1)

if __name__ == '__main__':
    migrate_issues() 