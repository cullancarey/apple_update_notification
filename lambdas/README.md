# Lambdas

This directory contains Lambda runtime code for scraping Apple release data and publishing update tweets.

## Files

- `apple_web_scrape.py` - Scheduled scraper. Fetches Apple's release page, extracts per-device versions/statements, and updates DynamoDB.
- `apple_send_update.py` - Stream processor. Handles DynamoDB stream `MODIFY` records and posts tweet updates.
- `apple_utils.py` - Shared helpers for AWS clients/resources, DynamoDB lookup, and Twitter authentication.
- `apple_subscription.py` - Placeholder for future subscription functionality.
- `apple_thank_you.py` - Placeholder for future post-signup automation.

## Runtime Inputs

- `apple_web_scrape` expects env var `dynamodb_table_name`.
- Both functions rely on SSM parameters prefixed with `apple_update_notification_` for Twitter secrets.

## Packaging

Lambda zip artifacts are built from repo root with:

```bash
./create_lambda_package.sh
```

The build includes handler code, `apple_utils.py`, and exported runtime dependencies.