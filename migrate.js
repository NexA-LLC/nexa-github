require('dotenv').config();
const { Octokit } = require('@octokit/rest');
const axios = require('axios');

// GitHubクライアントの初期化
const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN
});

// BitbucketのAPIエンドポイント
const BITBUCKET_API = 'https://api.bitbucket.org/2.0';

// Bitbucketの認証情報
const bitbucketAuth = {
  username: process.env.BITBUCKET_USERNAME,
  password: process.env.BITBUCKET_APP_PASSWORD
};

async function getBitbucketIssues() {
  try {
    const response = await axios.get(
      `${BITBUCKET_API}/repositories/${process.env.BITBUCKET_WORKSPACE}/${process.env.BITBUCKET_REPOSITORY}/issues`,
      {
        auth: bitbucketAuth,
        params: {
          q: process.env.BITBUCKET_JQL
        }
      }
    );
    return response.data.values;
  } catch (error) {
    console.error('Bitbucketのチケット取得に失敗しました:', error.message);
    throw error;
  }
}

async function createGitHubIssue(bitbucketIssue) {
  try {
    const issue = await octokit.issues.create({
      owner: process.env.GITHUB_OWNER,
      repo: process.env.GITHUB_REPOSITORY,
      title: bitbucketIssue.title,
      body: `# ${bitbucketIssue.title}\n\n${bitbucketIssue.content.raw}\n\n---\n\n移行元: Bitbucket Issue #${bitbucketIssue.id}`,
      labels: bitbucketIssue.kind ? [bitbucketIssue.kind] : []
    });

    // プロジェクトへの追加
    await octokit.projects.addCard({
      project_id: process.env.GITHUB_PROJECT_NUMBER,
      content_id: issue.data.node_id,
      content_type: 'Issue'
    });

    console.log(`チケットを作成しました: ${issue.data.html_url}`);
    return issue.data;
  } catch (error) {
    console.error(`GitHubチケットの作成に失敗しました (${bitbucketIssue.title}):`, error.message);
    throw error;
  }
}

async function migrateIssues() {
  try {
    console.log('Bitbucketからチケットを取得中...');
    const issues = await getBitbucketIssues();
    console.log(`${issues.length}件のチケットが見つかりました`);

    for (const issue of issues) {
      await createGitHubIssue(issue);
      // APIレート制限を考慮して少し待機
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log('移行が完了しました！');
  } catch (error) {
    console.error('移行中にエラーが発生しました:', error.message);
    process.exit(1);
  }
}

migrateIssues(); 