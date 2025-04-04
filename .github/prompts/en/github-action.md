First, please review the README.md.

Check the changes in commit ${GIT_HASH} for any issues with:

1. Code quality
   - Potential bugs
   - Security issues
   - Performance issues
   - Code readability
   - Adherence to best practices

2. Documentation quality (Markdown files)
   - Accuracy of content
   - Consistency
   - Readability
   - Appropriate formatting

3. Alignment with README.md guidelines
 Please suggest creating files according to the README.md concept if necessary.
 Documentation should be created in markdown format.

If issues are found, please propose specific fixes. If fixes are needed, automatically create a pull request.
If no fixes are needed, a Slack notification is sufficient.

Please send the review results to Slack in the following format:
```
Devin Review Result
Repository: ${GITHUB_REPOSITORY}
Branch: ${GITHUB_REF_NAME}
Commit: ${GIT_HASH}

Review result:
[Review result here]
```

Use the Webhook URL `${SLACK_WEB_HOOK}` to send the notification to Slack.

To create a pull request, use the token set in GITHUB_SECRET.
You can create a pull request with the following command:

```bash
curl -X POST \
  -H "Authorization: token ${GITHUB_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Pull request title",
    "body": "Pull request description",
    "head": "new branch name",
    "base": "${GITHUB_REF_NAME}"
  }' \
  https://api.github.com/repos/${GITHUB_REPOSITORY}/pulls
```
