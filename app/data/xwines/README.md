# X-Wines dataset drop-in directory

Place the X-Wines dataset files from `https://github.com/rogerioxavier/X-Wines` in this folder.

The API loader currently looks for these filenames:

- `wines.csv` (preferred)
- `wines.csv.gz`
- `wines.jsonl`

Expected common columns (best effort, optional):

- `wine_name` or `name`
- `winery_name` or `winery`
- `country`
- `region_1` or `region`
- `grapes` or `grape`
- `rating` or `average_rating`
- `num_reviews` or `reviews`

A tiny sample file is included so matching logic works in local tests.
