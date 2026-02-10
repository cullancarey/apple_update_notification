"""AWS Lambda function to tweet Apple release updates based on DynamoDB Streams."""

import sys
import logging
import random
from typing import Any, Dict

# Add the Lambda layer path for dependencies (e.g., apple_utils, tweepy, boto3)
sys.path.append("/opt")

try:
    from apple_utils import authenticate_twitter_client
except ImportError:
    from .apple_utils import authenticate_twitter_client

# -------------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# -------------------------------------------------------------------------
# Lambda Handler
# -------------------------------------------------------------------------
def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    """
    Processes DynamoDB stream records and tweets any new release updates.
    Invoked automatically by DynamoDB Streams → Lambda event mapping.
    """

    # Authenticate Twitter client once per invocation (avoid per-record overhead)
    try:
        twitter_client = authenticate_twitter_client()
        logger.info("Twitter client successfully authenticated.")
    except Exception as e:
        logger.error(f"Failed to authenticate Twitter client: {e}", exc_info=True)
        return

    for record in event["Records"]:
        try:
            dynamodb_data = record.get("dynamodb", {})
            if record.get("eventName") != "MODIFY":
                continue

            new_image = dynamodb_data["NewImage"]
            device_name = new_image.get("device", {}).get("S")
            release_statement = new_image.get("ReleaseStatement", {}).get("S")
            if not release_statement:
                logger.warning(
                    f"Missing ReleaseStatement for {device_name}, skipping tweet."
                )
                continue

            logger.info(
                f"Tweeting release update for {device_name or 'unknown device'}."
            )
            tweet_text = format_tweet(device_name, release_statement)
            post_tweet(twitter_client, tweet_text)

        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)

    logger.info("Lambda execution completed successfully.")


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
