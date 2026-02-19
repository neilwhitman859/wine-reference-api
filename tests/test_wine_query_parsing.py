import unittest
from unittest.mock import patch
import json

from fastapi.testclient import TestClient

from app.main import app


class _FakeResponse:
    output_text = """{
      \"summary\": \"Structured summary\",
      \"description_breakdown\": {
        \"producer_and_region\": \"Rioja\",
        \"grape_composition_and_style\": \"Tempranillo-led blend\",
        \"tasting_profile\": {
          \"aroma\": [\"red fruit\"],
          \"palate\": [\"savory\"],
          \"finish\": \"long\"
        },
        \"drinking_experience\": {
          \"body\": \"medium\",
          \"acidity\": \"fresh\",
          \"tannin\": \"polished\",
          \"alcohol_impression\": \"balanced\",
          \"serving_guidance\": \"decant 30 minutes\",
          \"food_pairings\": [\"lamb\"],
          \"cellaring_window\": \"now-2035\"
        }
      },
      \"vintage_intelligence\": {
        \"selected_vintage_assessment\": \"Excellent\",
        \"comparison_to_adjacent_vintages\": \"More concentrated than 2007\",
        \"weather_patterns\": [],
        \"buying_guidance\": \"Buy\"
      },
      \"uncertainty_notes\": []
    }"""


class _FakeOpenAI:
    last_input = ""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.responses = self

    def create(self, model: str, input: str):
        self.__class__.last_input = input
        return _FakeResponse()


class _FakeVinouResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {
                "data": {
                    "name": "Opus One",
                    "summary": "Authoritative producer data from Vinou.",
                    "producer": "Opus One Winery",
                    "region": "Napa Valley",
                    "grape_composition": "Cabernet Sauvignon-led blend",
                }
            }
        ).encode("utf-8")


class WineQueryParsingTests(unittest.TestCase):
    @patch("app.main.OpenAI", _FakeOpenAI)
    @patch("app.main.os.getenv", side_effect=lambda key: {"OPENAI_API_KEY": "test-key"}.get(key))
    def test_tondonia_vintage_in_name_is_parsed(self, _mock_getenv):
        client = TestClient(app)
        response = client.get("/explain-wine", params={"name": "Tondonia vintage 2008"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["wine"], "Tondonia")
        self.assertEqual(payload["vintage"], 2008)
        self.assertIn("growing_season_weather", payload)
        self.assertEqual(payload["data_source"], "openai")
        self.assertIn("- Bottle: Tondonia", _FakeOpenAI.last_input)
        self.assertIn("- Selected vintage: 2008", _FakeOpenAI.last_input)

    @patch("app.main.OpenAI", _FakeOpenAI)
    @patch("app.main.os.getenv", side_effect=lambda key: {"OPENAI_API_KEY": "test-key"}.get(key))
    def test_fort_ross_trailing_year_is_parsed(self, _mock_getenv):
        client = TestClient(app)
        response = client.get("/explain-wine", params={"name": "Fort Ross Top of Land 2020"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["wine"], "Fort Ross Top of Land")
        self.assertEqual(payload["vintage"], 2020)
        self.assertIn("growing_season_weather", payload)
        self.assertEqual(payload["data_source"], "openai")
        self.assertIn("- Bottle: Fort Ross Top of Land", _FakeOpenAI.last_input)
        self.assertIn("- Selected vintage: 2020", _FakeOpenAI.last_input)

    @patch("app.main.request.urlopen", return_value=_FakeVinouResponse())
    @patch("app.main.os.getenv", side_effect=lambda key: {"VINOU_API_URL": "https://vinou.example/api"}.get(key))
    def test_vinou_source_is_reported_when_available(self, _mock_getenv, _mock_urlopen):
        client = TestClient(app)
        response = client.get("/explain-wine", params={"name": "Opus One", "vintage": 2019})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data_source"], "vinou")
        self.assertIn("Vinou", payload["data_source_note"])
        self.assertEqual(payload["summary"], "Authoritative producer data from Vinou.")


if __name__ == "__main__":
    unittest.main()
