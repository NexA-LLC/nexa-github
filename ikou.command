以下みたいな処理があるんだけど... リポジトリ名を引数にして一通り実行して欲しいんだ
これでいうとwebapp-mangasenseiが引数だね

git clone git@github.com:NexA-LLC/webapp-mangasensei.git
git remote add upstream git@bitbucket.org:nex-a/webapp-mangasensei.git
cd webapp-mangasensei
git remote add upstream git@bitbucket.org:nex-a/webapp-mangasensei.git
git fetch upstream
git lfs fetch --all
git checkout -b upstream-main --track upstream/main
git status
git push origin main
git checkout main
git merge upstream-main
