from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone
import json
import os
import re
from urllib import parse, request

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI

from app.xwines import XWinesIndex

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
XWINES_INDEX = XWinesIndex.load_from_repo(BASE_DIR)


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

    dataset_match = XWINES_INDEX.search(parsed_name)
    dataset_context = dataset_match.to_prompt_block() if dataset_match else "No exact X-Wines dataset match found."

    prompt = f"""You are a professional sommelier and wine market analyst.

Provide a detailed JSON response for this wine:
- Bottle: {parsed_name}
- {vintage_context}
- {dataset_context}

Requirements:
1) Respond ONLY as valid JSON. No markdown, no prose outside JSON.
2) Keep every field concise, data-driven, and professional in tone.
3) Prioritize measurable statements (temperature/rainfall deviations, timing, relative ranking) over generic adjectives.
4) If certainty is low, include assumptions in the `uncertainty_notes` field.
5) Include weather-pattern-driven vintage insight based on broadly documented regional climate patterns and harvest timing.

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
  "climate_context": {{
    "region": "string",
    "latitude": "number",
    "longitude": "number",
    "growing_season": {{
      "start_month": "number",
      "start_day": "number",
      "end_month": "number",
      "end_day": "number"
    }}
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
        growing_season_weather = _build_growing_season_weather(
            climate_context=structured.get("climate_context", {}),
            selected_vintage=parsed_vintage,
        )

        return {
            "wine": parsed_name,
            "vintage": parsed_vintage,
            "summary": structured.get("summary"),
            "description_breakdown": structured.get("description_breakdown", {}),
            "vintage_intelligence": structured.get("vintage_intelligence", {}),
            "growing_season_weather": growing_season_weather,
            "xwines_dataset_match": dataset_match.to_response_payload() if dataset_match else None,
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


def _build_growing_season_weather(
    climate_context: dict[str, Any],
    selected_vintage: Optional[int],
) -> dict[str, Any]:
    latitude = _parse_float(climate_context.get("latitude"))
    longitude = _parse_float(climate_context.get("longitude"))
    if latitude is None or longitude is None:
        return {"error": "No usable location returned for growing season weather analysis."}

    season = climate_context.get("growing_season") or {}
    start_month = _safe_int(season.get("start_month"), 4)
    start_day = _safe_int(season.get("start_day"), 1)
    end_month = _safe_int(season.get("end_month"), 10)
    end_day = _safe_int(season.get("end_day"), 31)

    if (end_month, end_day) < (start_month, start_day):
        start_month, start_day, end_month, end_day = 4, 1, 10, 31

    current_year = datetime.now(timezone.utc).year
    end_year = current_year - 1
    start_year = min((selected_vintage or end_year), end_year) - 20
    start_year = max(start_year, 1980)
    if start_year > end_year:
        start_year = end_year

    daily = _fetch_open_meteo_history(
        latitude=latitude,
        longitude=longitude,
        start_date=f"{start_year:04d}-{start_month:02d}-{start_day:02d}",
        end_date=f"{end_year:04d}-{end_month:02d}-{end_day:02d}",
    )
    by_year = _aggregate_seasonal_metrics(
        daily=daily,
        start_month=start_month,
        start_day=start_day,
        end_month=end_month,
        end_day=end_day,
    )
    if not by_year:
        return {"error": "No weather records were available for the requested growing season."}

    years_sorted = sorted(by_year)
    all_years = [by_year[year] for year in years_sorted]
    average_year = _summarize_average_year(all_years)

    selected = by_year.get(selected_vintage) if selected_vintage else None
    comparisons = _build_comparisons(selected, average_year)

    return {
        "region": climate_context.get("region") or "Unknown region",
        "location": {"latitude": latitude, "longitude": longitude},
        "growing_season": {
            "start_month": start_month,
            "start_day": start_day,
            "end_month": end_month,
            "end_day": end_day,
        },
        "all_years_period": {"start_year": years_sorted[0], "end_year": years_sorted[-1]},
        "all_years_average": average_year,
        "selected_vintage": selected,
        "selected_vs_average_comparison": comparisons,
        "yearly_metrics": [{"year": year, **by_year[year]} for year in years_sorted],
    }


def _parse_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed


def _fetch_open_meteo_history(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, list[Any]]:
    params = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "UTC",
    }
    url = f"https://archive-api.open-meteo.com/v1/archive?{parse.urlencode(params)}"

    try:
        with request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Open-Meteo call failed: {exc}") from exc

    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise HTTPException(status_code=502, detail="Open-Meteo response did not include daily weather data.")
    return daily


def _aggregate_seasonal_metrics(
    daily: dict[str, list[Any]],
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
) -> dict[int, dict[str, float]]:
    dates = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_sum") or []

    length = min(len(dates), len(highs), len(lows), len(rain))
    season_by_year: dict[int, dict[str, list[float]]] = {}

    for idx in range(length):
        raw_date = dates[idx]
        try:
            stamp = datetime.strptime(raw_date, "%Y-%m-%d")
        except (TypeError, ValueError):
            continue

        month_day = (stamp.month, stamp.day)
        if month_day < (start_month, start_day) or month_day > (end_month, end_day):
            continue

        year_bucket = season_by_year.setdefault(
            stamp.year,
            {
                "highs": [],
                "lows": [],
                "rain": [],
            },
        )

        high = _parse_float(highs[idx])
        low = _parse_float(lows[idx])
        precipitation = _parse_float(rain[idx])
        if high is not None:
            year_bucket["highs"].append(high)
        if low is not None:
            year_bucket["lows"].append(low)
        if precipitation is not None:
            year_bucket["rain"].append(precipitation)

    summarized: dict[int, dict[str, float]] = {}
    for year, values in season_by_year.items():
        if not values["highs"] or not values["lows"]:
            continue
        rainy_days = sum(1 for entry in values["rain"] if entry >= 1.0)
        summarized[year] = {
            "avg_high_c": round(sum(values["highs"]) / len(values["highs"]), 2),
            "max_high_c": round(max(values["highs"]), 2),
            "avg_low_c": round(sum(values["lows"]) / len(values["lows"]), 2),
            "min_low_c": round(min(values["lows"]), 2),
            "rain_total_mm": round(sum(values["rain"]), 2),
            "rainy_days": rainy_days,
        }
    return summarized


def _summarize_average_year(all_years: list[dict[str, float]]) -> dict[str, float]:
    count = len(all_years)
    return {
        "avg_high_c": round(sum(item["avg_high_c"] for item in all_years) / count, 2),
        "max_high_c": round(sum(item["max_high_c"] for item in all_years) / count, 2),
        "avg_low_c": round(sum(item["avg_low_c"] for item in all_years) / count, 2),
        "min_low_c": round(sum(item["min_low_c"] for item in all_years) / count, 2),
        "rain_total_mm": round(sum(item["rain_total_mm"] for item in all_years) / count, 2),
        "rainy_days": round(sum(item["rainy_days"] for item in all_years) / count, 2),
    }


def _build_comparisons(
    selected_vintage: Optional[dict[str, float]],
    average_year: dict[str, float],
) -> dict[str, Optional[float]]:
    if not selected_vintage:
        return {
            "avg_high_delta_c": None,
            "max_high_vs_avg_high_delta_c": None,
            "avg_low_delta_c": None,
            "min_low_vs_avg_low_delta_c": None,
            "rain_total_delta_mm": None,
            "rainy_days_delta": None,
        }

    return {
        "avg_high_delta_c": round(selected_vintage["avg_high_c"] - average_year["avg_high_c"], 2),
        "max_high_vs_avg_high_delta_c": round(
            selected_vintage["max_high_c"] - average_year["avg_high_c"],
            2,
        ),
        "avg_low_delta_c": round(selected_vintage["avg_low_c"] - average_year["avg_low_c"], 2),
        "min_low_vs_avg_low_delta_c": round(selected_vintage["min_low_c"] - average_year["avg_low_c"], 2),
        "rain_total_delta_mm": round(selected_vintage["rain_total_mm"] - average_year["rain_total_mm"], 2),
        "rainy_days_delta": round(selected_vintage["rainy_days"] - average_year["rainy_days"], 2),
    }
