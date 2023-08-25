"""AWS SDK for Python"""
import sys

sys.path.append("/opt")
import logging
from apple_utils import (
    authenticate_twitter_client
)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main function for lambda function"""

    twitter_client = authenticate_twitter_client()

    for record in event['Records']:
        release_statement = record['dynamodb']['NewImage']['ReleaseStatement']['S']

        post_tweet(twitter_client=twitter_client, tweet_content=release_statement)

        

def post_tweet(twitter_client, tweet_content):
    try:
        # Post the tweet
        logger.info(f"Sending tweet with content: {tweet_content}")
        response = twitter_client.create_tweet(text=tweet_content)
    except Exception as e:
        logger.error(f"An error occurred creating tweet: {e}")
    else:
        logger.info(f"Tweet posted successfully! Tweet info: {response}")