# wine-reference-api

Simple FastAPI app that provides AI-generated wine overviews.

## Endpoints

- `GET /` — basic web UI for entering a wine and optional vintage.
- `GET /health` — healthcheck.
- `GET /explain-wine?name=<wine>&vintage=<optional-year>` — returns wine summary.

## Run locally (Codespaces + local machine)

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then test in the same terminal:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/
```

If those pass, open one of these URLs in your browser:

- Local machine: `http://127.0.0.1:8000/`
- Codespaces forwarded port URL (your `*.app.github.dev` link)

## Step-by-step testing guide (beginner friendly)

Use this sequence every time you make a change. It helps you catch problems early before you deploy.

### 1) Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

What "good" looks like in the terminal:
- `Application startup complete.`
- `Uvicorn running on http://0.0.0.0:8000`

Keep this terminal open while testing.

### 2) Run API smoke tests from a second terminal

Open a second terminal tab/window in the same repo and run:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/
```

Expected results:
- `/health` returns `HTTP/1.1 200 OK` with JSON like `{"status":"ok", ...}`.
- `/` returns `HTTP/1.1 200 OK` and HTML (`content-type: text/html`).

### 3) Test `/explain-wine` without a vintage

```bash
curl -i "http://127.0.0.1:8000/explain-wine?name=Opus%20One"
```

Expected results:
- If `OPENAI_API_KEY` is set: `200 OK` with JSON containing `wine`, `vintage`, and `explanation`.
- If key is missing: `500` with detail `OPENAI_API_KEY is not set in the server environment.`

### 4) Test `/explain-wine` with a vintage

```bash
curl -i "http://127.0.0.1:8000/explain-wine?name=Opus%20One&vintage=2018"
```

Expected results:
- If `OPENAI_API_KEY` is set: `200 OK` and response includes `"vintage": 2018`.
- If key is missing: same expected `500` as above.

### 5) Test the browser UI manually

1. Open `http://127.0.0.1:8000/` (or your Codespaces forwarded URL).
2. Enter a wine name only and submit.
3. Enter a wine name + vintage and submit.
4. Confirm both requests render a readable explanation block.

### 6) Optional: one-command quick check

This quick script runs the two safest checks (health + homepage):

```bash
curl -fsS http://127.0.0.1:8000/health >/dev/null && echo "health ok"
curl -fsS http://127.0.0.1:8000/ >/dev/null && echo "home ok"
```

If either command prints an error instead of `ok`, fix that before deploying.

## Common issues

- `ERR_CONNECTION_REFUSED` on `127.0.0.1:8000`
  - The server is not running yet (or crashed). Start it with the `uvicorn ...` command above and keep that terminal window open.

- `{"detail":"Not Found"}` on your `*.app.github.dev` URL
  - Usually means you are hitting the wrong service/port, or an old process is running on that port.
  - In Codespaces, confirm port `8000` is forwarded and points to the current running `uvicorn` process.
  - Re-run the health check: `curl -i http://127.0.0.1:8000/health`.

- `/explain-wine` returns a 500 error about API key
  - Set `OPENAI_API_KEY` in your shell before starting the server.


## Pull request conflicts (what to choose)

If GitHub or VS Code shows conflict buttons like **Accept Current**, **Accept Incoming**, or **Accept Both**, use this rule:

- **Accept Current**: keep the version from the branch you are currently on (usually your local checked-out branch).
- **Accept Incoming**: keep the version coming from the branch you are merging in.
- **Accept Both**: keep both blocks and then manually clean up duplicates/ordering.

### Practical way to choose

1. If one side only has documentation/comment changes and the other has real code changes, usually pick the code side and then re-apply docs if needed.
2. If both sides changed different parts of the same file and both are needed, choose **Accept Both** then edit the result into one clean final version.
3. After resolving, always run your smoke tests again before committing.

### Fast mode (incoming-first)

If your goal is to move fast, you can use an **incoming-first rule**:

- Default to **Accept Incoming** for most conflicts.
- Then run smoke tests immediately.
- If tests fail, restore the needed lines from the current branch version and re-test.

This gives speed first, then validation as your safety net.

### Quick conflict workflow

```bash
git status
# edit conflicted files and resolve markers
git add <resolved-files>
git commit
```

### About "number of simultaneous versions"

If you are seeing this in a merge or AI-assist UI, it means how many alternative merge/suggestion results are generated at once.

- Start with **1** if you are learning (less noise, easier to review).
- Use **2-3** only when a conflict is complex and you want options to compare.
- Higher numbers do **not** make merges safer by themselves; they just create more candidate outputs for you to review.

For your incoming-first workflow:
- Start with **1** simultaneous version for speed and clarity.
- Use **2** only when one incoming option fails tests and you want one alternative to compare quickly.


## Where your README updates are

If you do not see recent README changes in GitHub, the most common reason is branch mismatch:

- Your latest edits here are on branch `work` (not `main`).
- GitHub only shows a branch's files after that branch is pushed and selected in the branch dropdown, or after merge.

Quick check commands:

```bash
git branch --show-current
git log --oneline -n 5
```

If needed, push `work` and view that branch specifically in GitHub before merging.

## Environment variables

- `OPENAI_API_KEY` (required for `/explain-wine`)
