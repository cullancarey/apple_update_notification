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
        # device = record['dynamodb']['Keys']['device']['S']
        release_statement = record['dynamodb']['NewImage']['ReleaseStatement']['S']
        # release_version = record['dynamodb']['NewImage']['ReleaseVersion']['S']
        # time_created = record['dynamodb']['ApproximateCreationDateTime']
        # event_name = record['eventName']

        post_tweet(twitter_client=twitter_client, tweet_content=release_statement)

        

def post_tweet(twitter_client, tweet_content):
    try:
        # Post the tweet
        response = twitter_client.create_tweet(status=tweet_content)
        logger.info(f"Tweet posted successfully! Tweet ID: {response['id']}")
    except Exception as e:
        logger.error(f"An error occurred creating tweet: {e}")