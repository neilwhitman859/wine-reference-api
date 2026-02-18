# Agent Workflow (Codex + Codespaces + Render)

## Environment
- Work happens inside GitHub Codespaces (full git + gh access).
- Render deploys from the `main` branch with Auto Deploy enabled.
- Goal: any merged change to `main` should reflect on the live Render URL.

## Default flow (preferred)
1) `git checkout main && git pull origin main`
2) Create a branch: `git checkout -b feature/<short-name>`
3) Make the smallest change possible.
4) Run a quick smoke test:
   - `python -m compileall app/main.py`
   - (optional) start uvicorn and curl /health
5) Commit, push, open PR:
   - `git commit -am "<message>"` (or add + commit)
   - `git push -u origin <branch>`
   - `gh pr create --base main --head <branch> --title "<title>" --body "<verify steps>"`
6) Enable auto-merge on the PR (or merge immediately if checks pass):
   - `gh pr merge --squash --auto --delete-branch`
7) After merge, Render auto-deploys `main`.

## Constraints
- Keep changes small and focused.
- Do not refactor unrelated code.
- Never commit secrets; use Render env vars.
- Prefer squash merges.
