import unittest
from unittest.mock import patch

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


class WineQueryParsingTests(unittest.TestCase):
    @patch("app.main._build_growing_season_weather", return_value={"ok": True})
    @patch("app.main.OpenAI", _FakeOpenAI)
    @patch("app.main.os.getenv", return_value="test-key")
    def test_tondonia_vintage_in_name_is_parsed(self, _mock_getenv, _mock_weather):
        client = TestClient(app)
        response = client.get("/explain-wine", params={"name": "Tondonia vintage 2008"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["wine"], "Tondonia")
        self.assertEqual(payload["vintage"], 2008)
        self.assertIn("xwines_dataset_match", payload)
        self.assertEqual(payload["xwines_dataset_match"]["country"], "Spain")
        self.assertIn("Known X-Wines dataset match", _FakeOpenAI.last_input)
        self.assertIn("- Bottle: Tondonia", _FakeOpenAI.last_input)
        self.assertIn("- Selected vintage: 2008", _FakeOpenAI.last_input)

    @patch("app.main._build_growing_season_weather", return_value={"ok": True})
    @patch("app.main.OpenAI", _FakeOpenAI)
    @patch("app.main.os.getenv", return_value="test-key")
    def test_fort_ross_trailing_year_is_parsed(self, _mock_getenv, _mock_weather):
        client = TestClient(app)
        response = client.get("/explain-wine", params={"name": "Fort Ross Top of Land 2020"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["wine"], "Fort Ross Top of Land")
        self.assertEqual(payload["vintage"], 2020)
        self.assertEqual(payload["xwines_dataset_match"]["region"], "Sonoma Coast")
        self.assertIn("Known X-Wines dataset match", _FakeOpenAI.last_input)
        self.assertIn("- Bottle: Fort Ross Top of Land", _FakeOpenAI.last_input)
        self.assertIn("- Selected vintage: 2020", _FakeOpenAI.last_input)


if __name__ == "__main__":
    unittest.main()
