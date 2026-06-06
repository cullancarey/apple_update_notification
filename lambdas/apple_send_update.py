"""AWS Lambda function to tweet Apple release updates based on DynamoDB Streams."""

import os
import logging
import random
from typing import Any, Dict

try:
    from .apple_utils import (
        authenticate_twitter_client,
        create_dynamodb_resource,
        mark_tweet_posted,
    )
except ImportError:
    from apple_utils import (
        authenticate_twitter_client,
        create_dynamodb_resource,
        mark_tweet_posted,
    )

# -------------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE_ENV_VAR = "dynamodb_table_name"


# -------------------------------------------------------------------------
# Lambda Handler
# -------------------------------------------------------------------------
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Processes DynamoDB stream records and tweets any new release updates.
    Invoked automatically by DynamoDB Streams → Lambda event mapping.
    """

    records = event.get("Records", [])

    dynamodb_table_name = os.getenv(DYNAMODB_TABLE_ENV_VAR)
    if not dynamodb_table_name:
        logger.error("Environment variable '%s' is not set.", DYNAMODB_TABLE_ENV_VAR)
        return {
            "batchItemFailures": [
                {"itemIdentifier": r["eventID"]} for r in records if r.get("eventID")
            ]
        }

    dynamodb = create_dynamodb_resource()
    table = dynamodb.Table(dynamodb_table_name)

    # Authenticate Twitter client once per invocation (avoid per-record overhead)
    try:
        twitter_client = authenticate_twitter_client()
        logger.info("Twitter client successfully authenticated.")
    except Exception as e:
        logger.error(f"Failed to authenticate Twitter client: {e}", exc_info=True)
        return {
            "batchItemFailures": [
                {"itemIdentifier": r["eventID"]} for r in records if r.get("eventID")
            ]
        }

    failures = []

    for record in records:
        event_id = record.get("eventID")
        try:
            dynamodb_data = record.get("dynamodb", {})
            if record.get("eventName") != "MODIFY":
                continue

            new_image = dynamodb_data.get("NewImage", {})
            device_name = new_image.get("device", {}).get("S")
            release_version = new_image.get("ReleaseVersion", {}).get("S")
            release_statement = new_image.get("ReleaseStatement", {}).get("S")
            if not release_statement or not release_version or not device_name:
                logger.warning(
                    "Missing required stream fields for event %s, skipping tweet.",
                    event_id,
                )
                continue

            if not mark_tweet_posted(table, device_name, release_version):
                continue

            logger.info(
                f"Tweeting release update for {device_name or 'unknown device'}."
            )
            tweet_text = format_tweet(device_name, release_statement)
            post_tweet(twitter_client, tweet_text)

        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            if event_id:
                failures.append({"itemIdentifier": event_id})

    logger.info("Lambda execution completed with %d failed records.", len(failures))
    return {"batchItemFailures": failures}


# -------------------------------------------------------------------------
# Tweet Posting Function
# -------------------------------------------------------------------------
def post_tweet(twitter_client: Any, tweet_content: str) -> None:
    """
    Posts a tweet using the authenticated Tweepy client.
    Wraps all exceptions and logs structured responses.
    """

    try:
        logger.info(f"Posting tweet: {tweet_content}")
        response = twitter_client.create_tweet(text=tweet_content)
        logger.info(f"Tweet successfully posted. Response: {response}")
    except Exception as e:
        logger.error(f"Error posting tweet: {e}", exc_info=True)
        raise


def format_tweet(device: str, release: str) -> str:
    """Return an engaging tweet for a given Apple OS release."""
    # Short brand emojis and intros
    emojis = ["🍏", "🚀", "🔥", "✨", "📱", "💻", "⌚️", "🖥️", "👓"]
    intros = [
        "Just dropped!",
        "New update rolling out now.",
        "Heads up — new release alert!",
        "Apple’s latest update is here.",
        "Fresh off Cupertino’s servers:",
    ]
    hashtags = {
        "iOS": "#iOS #Apple",
        "macOS": "#macOS #Apple",
        "watchOS": "#watchOS #AppleWatch",
        "tvOS": "#tvOS #AppleTV",
        "visionOS": "#visionOS #AppleVisionPro",
    }

    emoji = random.choice(emojis)
    intro = random.choice(intros)
    hashtag_str = hashtags.get(device, "#Apple")

    tweet = f"{emoji} {intro}\n\n{release}\n\n{hashtag_str}"
    return tweet
