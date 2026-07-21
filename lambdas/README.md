# Lambdas

This directory contains Lambda runtime code for scraping Apple release data and sending release notification emails.

## Files

- `apple_web_scrape.py` - Scheduled scraper. Fetches Apple's release page, extracts per-device versions/statements, and updates DynamoDB.
- `apple_utils.py` - Shared helpers for AWS clients/resources, DynamoDB lookup, and SNS notifications.
- `apple_subscription.py` - Placeholder for future subscription functionality.
- `apple_thank_you.py` - Placeholder for future post-signup automation.

## Runtime Inputs

- `apple_web_scrape` expects env var `dynamodb_table_name`.
- `apple_web_scrape` also expects env var `release_notification_topic_arn`.
- Both functions can publish error notifications when `error_alert_topic_arn` is configured.

## Packaging

Lambda zip artifacts are built from repo root with:

```bash
./create_lambda_package.sh
```

The build includes handler code, `apple_utils.py`, and exported runtime dependencies.