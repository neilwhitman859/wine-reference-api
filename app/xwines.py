from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import csv
import json
import re


@dataclass
class WineDatasetMatch:
    wine_name: str
    winery: Optional[str]
    country: Optional[str]
    region: Optional[str]
    grape: Optional[str]
    avg_rating: Optional[float]
    num_ratings: Optional[int]

    def to_prompt_block(self) -> str:
        return (
            "Known X-Wines dataset match:\n"
            f"- wine_name: {self.wine_name}\n"
            f"- winery: {self.winery or 'unknown'}\n"
            f"- country: {self.country or 'unknown'}\n"
            f"- region: {self.region or 'unknown'}\n"
            f"- grape: {self.grape or 'unknown'}\n"
            f"- avg_rating: {self.avg_rating if self.avg_rating is not None else 'unknown'}\n"
            f"- num_ratings: {self.num_ratings if self.num_ratings is not None else 'unknown'}"
        )

    def to_response_payload(self) -> dict[str, Any]:
        return {
            "wine_name": self.wine_name,
            "winery": self.winery,
            "country": self.country,
            "region": self.region,
            "grape": self.grape,
            "avg_rating": self.avg_rating,
            "num_ratings": self.num_ratings,
        }


class XWinesIndex:
    def __init__(self, rows: list[dict[str, str]]):
        self.rows = rows

    @classmethod
    def load_from_repo(cls, base_dir: Path) -> "XWinesIndex":
        data_dir = base_dir / "data" / "xwines"
        candidates = [
            data_dir / "wines.csv",
            data_dir / "wines.csv.gz",
            data_dir / "wines.jsonl",
        ]
        for path in candidates:
            if path.exists():
                rows = _read_rows(path)
                if rows:
                    return cls(rows)
        return cls([])

    def search(self, wine_name: str) -> Optional[WineDatasetMatch]:
        if not self.rows:
            return None

        target_tokens = set(_tokenize(wine_name))
        if not target_tokens:
            return None

        best_row: Optional[dict[str, str]] = None
        best_score = 0.0

        for row in self.rows:
            name = row.get("wine_name") or row.get("name") or ""
            if not name:
                continue
            row_tokens = set(_tokenize(name))
            if not row_tokens:
                continue

            overlap = len(target_tokens & row_tokens)
            score = overlap / max(len(target_tokens), len(row_tokens))
            if score > best_score:
                best_score = score
                best_row = row

        if not best_row or best_score < 0.4:
            return None

        return WineDatasetMatch(
            wine_name=best_row.get("wine_name") or best_row.get("name") or wine_name,
            winery=best_row.get("winery_name") or best_row.get("winery"),
            country=best_row.get("country"),
            region=best_row.get("region_1") or best_row.get("region"),
            grape=best_row.get("grapes") or best_row.get("grape"),
            avg_rating=_to_float(best_row.get("rating") or best_row.get("average_rating")),
            num_ratings=_to_int(best_row.get("num_reviews") or best_row.get("reviews")),
        )


def _read_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix == ".jsonl":
        rows: list[dict[str, str]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    rows.append({str(k): str(v) for k, v in parsed.items()})
        return rows

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if row]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
