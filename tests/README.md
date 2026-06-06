# Tests

Pytest test suite for Lambda behavior.

## Files

- `test_apple_web_scrape_lambda.py` - Tests parsing and DynamoDB update behavior for scraper logic.
- `test_apple_send_update_lambda.py` - Tests stream processing and tweet-post flow behavior.

## Run

From repo root:

```bash
uv run pytest -v
```

or:

```bash
python -m pytest -v tests
```

Tests are written to avoid live AWS/Twitter calls and should run locally with mocked dependencies.