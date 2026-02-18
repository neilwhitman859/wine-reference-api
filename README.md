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

## Common issues

- `ERR_CONNECTION_REFUSED` on `127.0.0.1:8000`
  - The server is not running yet (or crashed). Start it with the `uvicorn ...` command above and keep that terminal window open.

- `{"detail":"Not Found"}` on your `*.app.github.dev` URL
  - Usually means you are hitting the wrong service/port, or an old process is running on that port.
  - In Codespaces, confirm port `8000` is forwarded and points to the current running `uvicorn` process.
  - Re-run the health check: `curl -i http://127.0.0.1:8000/health`.

- `/explain-wine` returns a 500 error about API key
  - Set `OPENAI_API_KEY` in your shell before starting the server.

## Environment variables

- `OPENAI_API_KEY` (required for `/explain-wine`)
