# wine-reference-api

Simple FastAPI app that provides AI-generated wine overviews.

For AI agent and contributor workflow, see AGENT_WORKFLOW.md

## Endpoints

- `GET /` — basic web UI for entering a wine and optional vintage.
- `GET /health` — healthcheck.
- `GET /explain-wine?name=<wine>&vintage=<optional-year>` — returns wine summary.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

## Environment variables

- `WINEVYBE_API_URL` (optional, preferred first-party wine source)
- `WINEVYBE_API_KEY` (optional bearer token for WineVybe)
- `VINOU_API_URL` (optional secondary wine source)
- `VINOU_API_KEY` (optional bearer token for Vinou)
- `OPENAI_API_KEY` (required only when neither WineVybe nor Vinou returns data)


## Playwright troubleshooting (for screenshot/e2e runs)

If Playwright cannot find `#name` or returns a 404 while the API seems up, use this checklist:

1. **Use a non-default app port** (for example `8123`) when launching uvicorn.
   - In some environments, `localhost:8000` inside browser automation can map to another service.
2. **Forward the same port to Playwright** and navigate to `http://localhost:<port>`.
3. **Prefer Firefox in constrained containers** if Chromium crashes with `SIGSEGV`.

Example server command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8123
```

Example Playwright snippet:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch()
    page = browser.new_page()
    page.goto("http://localhost:8123", wait_until="domcontentloaded")
    page.wait_for_selector("#name", timeout=15000)
```


## Fast UI iteration loop (recommended)

Use the helper script below when you want a reliable screenshot-driven workflow for iterative UI edits:

```bash
pip install -r requirements.txt
python -m playwright install firefox
python scripts/ui_loop.py --name "Opus One" --vintage 2019 --out artifacts/ui.png
```

Why this works well in this container:
- Uses a dedicated app port (`8123` by default).
- Waits for the app to be ready before browser actions.
- Uses **Playwright Firefox** (more stable than Chromium here).
- Produces a screenshot artifact you can review between edits.
