まずREADME.mdは一度目を通してください。

コミット ${GIT_HASH} の変更を確認し、以下の点について問題がないかチェックしてください：

1. コードの品質
   - バグの可能性
   - セキュリティの問題
   - パフォーマンスの問題
   - コードの可読性
   - ベストプラクティスの遵守

2. ドキュメント（Markdownファイル）の品質
   - 内容の正確性
   - 一貫性
   - 可読性
   - フォーマットの適切性

3. README.mdの方針に合っているかどうかの品質
 必要に応じてREADME.mdのコンセプトに沿ってファイルを作る提案などもしてください。
 ドキュメント類はmarkdownフォーマットで作成します。

問題が見つかった場合も、具体的な修正案を提案してください。修正が必要な場合は、自動的にプルリクエストを作成します。
修正が必要じゃ無い場合はslackヘの通知のみで大丈夫です

レビュー結果は以下の形式でSlackに通知してください：
```
Devinレビュー結果
リポジトリ: ${GITHUB_REPOSITORY}
ブランチ: ${GITHUB_REF_NAME}
コミット: ${GIT_HASH}

レビュー結果:
[ここにレビュー結果を記載]
```

Slackへの通知は、Webhook URL `${SLACK_WEB_HOOK}` を使用して送信してください。

プルリクエストの作成には、GITHUB_SECRETに設定されているトークンを使用してください。
以下のコマンドでプルリクエストを作成できます：

```bash
curl -X POST \
  -H "Authorization: token ${GITHUB_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "プルリクエストのタイトル",
    "body": "プルリクエストの説明",
    "head": "新しいブランチ名",
    "base": "${GITHUB_REF_NAME}"
  }' \
  https://api.github.com/repos/${GITHUB_REPOSITORY}/pulls
``` 