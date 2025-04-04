import os
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description='GitHubのIssueステータスを更新するスクリプト')
parser.add_argument('project_id', type=int, help='GitHubプロジェクトID')
parser.add_argument('--repo', default='NexA-LLC/unity-sabong-client', help='リポジトリ名 (例: owner/repo)')
parser.add_argument('--token', help='GitHub APIトークン (環境変数 GH_TOKEN も使用可能)')
args = parser.parse_args()

github_token = args.token or os.getenv('GH_TOKEN')
if not github_token:
    raise ValueError("GitHub APIトークンが必要です。--tokenオプションまたは環境変数GH_TOKENを設定してください。")

def escape_string(s):
    """GraphQLの文字列をエスケープ"""
    if s is None:
        return ""
    return str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

def get_project_id(org_name, project_number):
    """組織のプロジェクトIDを取得"""
    headers = {
        'Authorization': f'token {github_token}',
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

def get_status_field_id(project_id):
    """プロジェクトのステータスフィールドIDを取得"""
    headers = {
        'Authorization': f'token {github_token}',
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
    
    fields = data['data']['node']['fields']['nodes']
    status_field = next((f for f in fields if f.get('name', '').lower() == 'status'), None)
    
    if not status_field:
        raise Exception("ステータスフィールドが見つかりません")
    
    return status_field

def get_repository_issues(owner, repo):
    """リポジトリのIssueを取得"""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    issues = []
    page = 1
    per_page = 100
    
    while True:
        response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/issues',
            headers=headers,
            params={'state': 'all', 'per_page': per_page, 'page': page}
        )
        
        if response.status_code != 200:
            raise Exception(f"Issueの取得に失敗: {response.text}")
        
        page_issues = response.json()
        if not page_issues:
            break
            
        issues.extend(page_issues)
        page += 1
    
    return issues

def get_project_items(project_id):
    """プロジェクトのアイテムを取得（IssueとDraftIssue両方）"""
    headers = {
        'Authorization': f'token {github_token}',
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
                            ... on Issue {
                                id
                                number
                                title
                                body
                                repository {
                                    name
                                    owner {
                                        login
                                    }
                                }
                            }
                            ... on DraftIssue {
                                id
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
        raise Exception(f"プロジェクトアイテムの取得に失敗: {response.text}")
    
    data = response.json()
    if 'errors' in data:
        raise Exception(f"プロジェクトアイテムの取得に失敗: {data['errors']}")
    
    return data['data']['node']['items']['nodes']

def update_item_status(project_id, item_id, status_field_id, status_option_id):
    """プロジェクトアイテムのステータスを更新"""
    headers = {
        'Authorization': f'token {github_token}',
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
    """ % (project_id, item_id, status_field_id, status_option_id)
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': mutation}
    )
    
    if response.status_code != 200:
        print(f"警告: ステータスの更新に失敗: {response.text}")
        return False
    
    data = response.json()
    if 'errors' in data:
        print(f"警告: ステータスの更新に失敗: {data['errors']}")
        return False
    
    return True

def add_issue_to_project(project_id, issue_node_id):
    """Issueをプロジェクトに追加"""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    mutation = """
    mutation {
        addProjectV2ItemById(input: {
            projectId: "%s"
            contentId: "%s"
        }) {
            item {
                id
            }
        }
    }
    """ % (project_id, issue_node_id)
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': mutation}
    )
    
    if response.status_code != 200:
        print(f"警告: Issueのプロジェクト追加に失敗: {response.text}")
        return None
    
    data = response.json()
    if 'errors' in data:
        print(f"警告: Issueのプロジェクト追加に失敗: {data['errors']}")
        return None
    
    return data['data']['addProjectV2ItemById']['item']['id']

def get_issue_node_id(owner, repo, issue_number):
    """IssueのノードIDを取得"""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    query = """
    query {
        repository(owner: "%s", name: "%s") {
            issue(number: %d) {
                id
                title
                body
            }
        }
    }
    """ % (owner, repo, issue_number)
    
    response = requests.post(
        'https://api.github.com/graphql',
        headers=headers,
        json={'query': query}
    )
    
    if response.status_code != 200:
        print(f"警告: IssueのノードID取得に失敗: {response.text}")
        return None, None
    
    data = response.json()
    if 'errors' in data:
        print(f"警告: IssueのノードID取得に失敗: {data['errors']}")
        return None, None
    
    return data['data']['repository']['issue']['id'], data['data']['repository']['issue']

def main():
    owner, repo = args.repo.split('/')
    
    project_number = args.project_id
    project_id = get_project_id(owner, project_number)
    print(f"プロジェクトID: {project_id}")
    
    status_field = get_status_field_id(project_id)
    print(f"ステータスフィールド: {status_field['name']} (ID: {status_field['id']})")
    print(f"利用可能なステータス: {[opt['name'] for opt in status_field['options']]}")
    
    done_option = next((opt for opt in status_field['options'] if opt['name'].lower() == 'done'), None)
    if not done_option:
        raise Exception("'Done'ステータスが見つかりません")
    
    print(f"'Done'ステータスID: {done_option['id']}")
    
    issues = get_repository_issues(owner, repo)
    print(f"{len(issues)}個のIssueが見つかりました")
    
    project_items = get_project_items(project_id)
    print(f"{len(project_items)}個のプロジェクトアイテムが見つかりました")
    
    project_issue_numbers = []
    for item in project_items:
        if item['content'] and 'number' in item['content']:
            project_issue_numbers.append(item['content']['number'])
    
    updated_count = 0
    
    for issue in issues:
        issue_number = issue['number']
        issue_body = issue.get('body', '')
        
        if issue_body and "Status: Done" in issue_body:
            print(f"Issue #{issue_number} '{issue['title']}' に 'Status: Done' が含まれています")
            
            item = next((item for item in project_items if item['content'] and item['content'].get('number') == issue_number), None)
            
            if not item:
                print(f"Issue #{issue_number} はプロジェクトに含まれていません。追加します...")
                node_id, issue_data = get_issue_node_id(owner, repo, issue_number)
                if node_id:
                    item_id = add_issue_to_project(project_id, node_id)
                    if item_id:
                        print(f"Issue #{issue_number} をプロジェクトに追加しました (ID: {item_id})")
                        
                        if update_item_status(project_id, item_id, status_field['id'], done_option['id']):
                            updated_count += 1
                            print(f"Issue #{issue_number} のステータスを更新しました")
            else:
                print(f"Issue #{issue_number} '{issue['title']}' のステータスを 'Done' に更新します...")
                if update_item_status(project_id, item['id'], status_field['id'], done_option['id']):
                    updated_count += 1
                    print(f"Issue #{issue_number} のステータスを更新しました")
    
    draft_updated_count = 0
    for item in project_items:
        if item['content'] and 'number' not in item['content']:
            item_title = item['content'].get('title', '')
            item_body = item['content'].get('body', '')
            
            if item_body and ("ステータス: Done" in item_body or "Status: Done" in item_body):
                print(f"ドラフト: '{item_title}' に 'ステータス: Done' が含まれています")
                print(f"ドラフト '{item_title}' のステータスを 'Done' に更新します...")
                
                if update_item_status(project_id, item['id'], status_field['id'], done_option['id']):
                    draft_updated_count += 1
                    print(f"ドラフト '{item_title}' のステータスを更新しました")
    
    print(f"合計 {updated_count} 個のIssueと {draft_updated_count} 個のドラフトアイテムのステータスを更新しました")

if __name__ == "__main__":
    main()