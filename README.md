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

- `OPENAI_API_KEY` (required for `/explain-wine`)
# codespace test
