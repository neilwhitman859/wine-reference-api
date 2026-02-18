from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")



@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2026-02-18 001",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/explain-wine")
def explain_wine(name: str, vintage: int):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the server environment.",
        )

    client = OpenAI(api_key=api_key)

    prompt = f"""You are a professional sommelier.

Provide a detailed but approachable overview of this wine:
- Bottle: {name}
- Selected vintage: {vintage}

Format your response with clear section headings and include:
1. Wine Overview
   - Producer and region context
   - Grape composition (if known) and style
   - Typical tasting notes (aroma, palate, finish)
2. Drinking Experience
   - Body, acidity, tannin, alcohol impression
   - Food pairing suggestions
   - Cellaring/serving guidance
3. Vintage Comparison (same bottle)
   - How the selected {vintage} compares with other nearby vintages from the same producer/wine
   - Notable weather or harvest effects when relevant
   - Whether {vintage} is generally stronger, weaker, or stylistically different than surrounding years
4. Buying Guidance
   - What type of drinker this vintage suits
   - Relative value and when to drink

If exact historical data is uncertain, state assumptions clearly and avoid fabrication.
"""

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        explanation = resp.output_text

        return {
            "wine": name,
            "vintage": vintage,
            "explanation": explanation,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI call failed: {repr(e)}")
