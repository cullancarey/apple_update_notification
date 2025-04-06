"""AWS Lambda Function to Tweet Updates Based on DynamoDB Streams"""

import sys

sys.path.append("/opt")

import logging
from apple_utils import authenticate_twitter_client

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main AWS Lambda handler function to process DynamoDB stream events and tweet updates."""

    # Authenticate Twitter client once per Lambda invocation
    twitter_client = authenticate_twitter_client()

    # Validate and process each DynamoDB record
    for record in event.get("Records", []):
        try:
            if "dynamodb" not in record or "NewImage" not in record["dynamodb"]:
                logger.warning("Record missing DynamoDB or NewImage key; skipping.")
                continue

            release_statement = (
                record["dynamodb"]["NewImage"].get("ReleaseStatement", {}).get("S")
            )
            if not release_statement:
                logger.warning("ReleaseStatement missing from record; skipping.")
                continue

            post_tweet(twitter_client, release_statement)

        except Exception as e:
            logger.error(f"Unexpected error processing record: {e}", exc_info=True)


def post_tweet(twitter_client, tweet_content):
    """Posts a tweet using the authenticated Twitter client."""
    try:
        logger.info(f"Attempting to tweet: {tweet_content}")
        response = twitter_client.create_tweet(text=tweet_content)
        logger.info(f"Tweet successfully posted: {response}")
    except Exception as e:
        logger.error(f"Error posting tweet: {e}", exc_info=True)
