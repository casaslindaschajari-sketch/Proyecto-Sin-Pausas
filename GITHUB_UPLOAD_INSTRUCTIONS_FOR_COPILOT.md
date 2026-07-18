# Instructions for Copilot: Upload Sabrina AI Lab Project to GitHub

You are working inside the VM/project folder:

```bash
/home/Sabrina
```

The target GitHub repository is:

```text
https://github.com/casaslindaschajari-sketch/Proyecto-Sin-Pausas
```

## Goal

Make sure the Sabrina AI Lab MVP is committed and uploaded to GitHub.

The important project files are:

```text
README.md
.gitignore
proyectos/sabrina_ai_lab/app.py
proyectos/sabrina_ai_lab/README.md
```

Do not upload secrets, credentials, `.env` files, SQLite runtime data, caches, or VS Code server files.

## What the app is

This is a functional web MVP with backend:

- Python HTTP server with no external dependencies.
- Frontend embedded in `app.py`.
- SQLite persistence.
- Lead capture.
- Commercial value calculator.
- Strategic assistant with local fallback.
- Optional LiteLLM / Azure OpenAI integration.
- Documentation in README files.

Run it with:

```bash
python3 proyectos/sabrina_ai_lab/app.py
```

Open:

```text
http://127.0.0.1:8000
```

## Step 1: Check current Git state

Run:

```bash
cd /home/Sabrina
git status -sb
git log --oneline --decorate -5
git remote -v
```

Expected remote:

```text
origin  https://github.com/casaslindaschajari-sketch/Proyecto-Sin-Pausas.git
```

If the remote is missing or wrong, configure it:

```bash
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/casaslindaschajari-sketch/Proyecto-Sin-Pausas.git
```

## Step 2: Make sure only safe files are tracked

The repository should track only the MVP files unless the user explicitly asks to upload more.

Recommended files to stage:

```bash
git add README.md .gitignore proyectos/sabrina_ai_lab/app.py proyectos/sabrina_ai_lab/README.md
```

Do not run `git add .` from `/home/Sabrina`, because it may include private/system files such as:

```text
.ssh/
.vscode-server/
.cache/
.claude/
.cline/
.env
*.sqlite3
proyectos/sabrina_ai_lab/data/
```

## Step 3: Commit changes if needed

Check if there are staged or modified MVP files:

```bash
git status --short
```

If there are changes to the MVP files, commit them:

```bash
git commit -m "Update Sabrina AI Lab MVP"
```

If Git says there is nothing to commit, continue to the push step.

## Step 4: Authenticate GitHub

If pushing over HTTPS, authenticate using GitHub credentials or a personal access token.

A GitHub token should have permission to push to:

```text
casaslindaschajari-sketch/Proyecto-Sin-Pausas
```

Recommended token scope for a classic token:

```text
repo
```

Do not paste secrets into files or commit them.

## Step 5: Push to GitHub

Run:

```bash
git branch -M main
git push -u origin main
```

If the repository already has commits and Git rejects the push because histories differ, first inspect the situation:

```bash
git fetch origin
git log --oneline --decorate --graph --all --max-count=20
```

If the remote repo is supposed to be replaced by this local MVP and the user approves, use:

```bash
git push -u origin main --force-with-lease
```

Only force push if the user confirms that overwriting remote history is acceptable.

## Step 6: Verify upload

Run:

```bash
git status -sb
git branch -vv
git ls-remote --heads origin main
git rev-parse HEAD
```

Success means:

- `git status -sb` shows `## main...origin/main`.
- `git branch -vv` shows `main` tracking `origin/main`.
- `git ls-remote --heads origin main` shows the same commit hash as `git rev-parse HEAD`.

Example success format:

```text
b604a1fdbd42c2e013f5c09b3370208678afeaa5 refs/heads/main
```

## Step 7: Final message to the user

After the push is verified, tell the user:

```text
The Sabrina AI Lab MVP has been uploaded to:

https://github.com/casaslindaschajari-sketch/Proyecto-Sin-Pausas

The local main branch is tracking origin/main, and the remote commit matches the local HEAD.
```

## Useful app commands

Run locally:

```bash
python3 proyectos/sabrina_ai_lab/app.py
```

Run exposed on the VM:

```bash
SABRINA_HOST=0.0.0.0 SABRINA_PORT=8000 python3 proyectos/sabrina_ai_lab/app.py
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

State API:

```bash
curl http://127.0.0.1:8000/api/state
```

## Important security note

Never commit:

```text
.env
Azure keys
GitHub tokens
SSH private keys
SQLite runtime databases
VS Code server folders
cache folders
```

The `.gitignore` already excludes common runtime data and secrets, but still avoid `git add .` from the home directory unless you have reviewed every file.