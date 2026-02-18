from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone
import json
import os
import re

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
        "version": "2026-02-18 002",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "OpenAI returned non-JSON output. "
                "Try again with a more specific wine name and vintage."
            ),
        ) from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=500, detail="OpenAI returned invalid JSON payload.")

    return parsed


@app.get("/explain-wine")
def explain_wine(name: str, vintage: Optional[int] = None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the server environment.",
        )

    client = OpenAI(api_key=api_key)

    parsed_name, parsed_vintage = _normalize_wine_query(name=name, vintage=vintage)
    vintage_context = (
        f"Selected vintage: {parsed_vintage}"
        if parsed_vintage
        else "No specific vintage selected"
    )

    prompt = f"""You are a professional sommelier and wine market analyst.

Provide a detailed JSON response for this wine:
- Bottle: {parsed_name}
- {vintage_context}

Requirements:
1) Respond ONLY as valid JSON. No markdown, no prose outside JSON.
2) Keep every field concise but informative.
3) If certainty is low, include assumptions in the `uncertainty_notes` field.
4) Include weather-pattern-driven vintage insight based on broadly documented regional climate patterns and harvest timing.

Use this exact JSON shape:
{{
  "wine_name": "string",
  "requested_vintage": "number or null",
  "summary": "2-4 sentence approachable summary",
  "description_breakdown": {{
    "producer_and_region": "string",
    "grape_composition_and_style": "string",
    "tasting_profile": {{
      "aroma": ["string"],
      "palate": ["string"],
      "finish": "string"
    }},
    "drinking_experience": {{
      "body": "string",
      "acidity": "string",
      "tannin": "string",
      "alcohol_impression": "string",
      "serving_guidance": "string",
      "food_pairings": ["string"],
      "cellaring_window": "string"
    }}
  }},
  "vintage_intelligence": {{
    "selected_vintage_assessment": "string",
    "comparison_to_adjacent_vintages": "string",
    "weather_patterns": [
      {{
        "period": "string",
        "pattern": "string",
        "impact_on_grapes": "string",
        "quality_signal": "string"
      }}
    ],
    "buying_guidance": "string"
  }},
  "uncertainty_notes": ["string"]
}}
"""

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        raw_output = resp.output_text
        if not raw_output:
            raise HTTPException(
                status_code=500,
                detail="OpenAI returned an empty response.",
            )
        structured = _extract_json_payload(raw_output)

        return {
            "wine": parsed_name,
            "vintage": parsed_vintage,
            "summary": structured.get("summary"),
            "description_breakdown": structured.get("description_breakdown", {}),
            "vintage_intelligence": structured.get("vintage_intelligence", {}),
            "uncertainty_notes": structured.get("uncertainty_notes", []),
            "raw_openai_payload": structured,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI call failed: {repr(e)}")


def _normalize_wine_query(name: str, vintage: Optional[int]) -> tuple[str, Optional[int]]:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="Wine name cannot be empty.")

    if vintage is not None:
        return normalized_name, vintage

    match = re.search(r"(?:\bvintage\s+)?(19\d{2}|20\d{2}|2100)\b", normalized_name, flags=re.IGNORECASE)
    if not match:
        return normalized_name, None

    parsed_vintage = int(match.group(1))
    cleaned_name = re.sub(
        r"\s*(?:\bvintage\s+)?(?:19\d{2}|20\d{2}|2100)\b\s*",
        " ",
        normalized_name,
        flags=re.IGNORECASE,
    )
    cleaned_name = re.sub(r"\s{2,}", " ", cleaned_name).strip(" ,.-")
    return cleaned_name or normalized_name, parsed_vintage
