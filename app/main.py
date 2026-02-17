from fastapi import FastAPI, HTTPException
import os
from openai import OpenAI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "version": "2026-02-17a"}


@app.get("/explain-wine")
def explain_wine(name: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the server environment."
        )

    client = OpenAI(api_key=api_key)

    prompt = f"""Explain this wine in simple terms: {name}

Describe:
- Likely flavor profile
- Body and acidity
- Who might enjoy it
"""

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        # Responses API returns text via output_text convenience
        explanation = resp.output_text

        return {"wine": name, "explanation": explanation}

    except Exception as e:
        # This surfaces the real reason (auth, model name, networking, etc.)
        raise HTTPException(status_code=500, detail=f"OpenAI call failed: {repr(e)}")
