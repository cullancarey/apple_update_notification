"""module for python aws sdk"""
import boto3
import tweepy
import os
import logging
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_param(param):
    """Retrieves parameter secrets from Parameter Store"""
    logger.info(f"Retrieving parameter {param}.")
    client = boto3.client("ssm")
    response = client.get_parameter(Name=param, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_item(table, today):
    """Retrieves latest releases item from DynamoDB table"""
    logger.info("Retrieving item from Dynamo.")
    try:
        response = table.scan(
            Limit=5,
            ScanFilter={
                "timestamp": {"ComparisonOperator": "GT", "AttributeValueList": [today]}
            }
        )
    except ClientError as err:
        logger.error(f"Exception ocurred retrieving item from DynamoDB: {err}")
    else:
        if response["Items"]:
            items = response['Items']
            logger.info(
                f"Successfully retrieved item from DynamoDB: {items}"
            )
            # Sort items by timestamp in descending order
            sorted_items = sorted(items, key=lambda x: x['timestamp'], reverse=True)
            return sorted_items[0]
        else:
            logger.error(
                f"Unable to find latest item from table: {table}."
            )
            return False


def authenticate_twitter_client():
    """Gets authenticated session from Twitter"""
    logger.info("Creating twitter client.")
    client_id = get_param(
        f"apple_update_notification_api_key_{os.environ['environment']}"
    )
    access_token = get_param(
        f"apple_update_notification_twitter_access_token_{os.environ['environment']}"
    )
    access_token_secret = get_param(
        f"apple_update_notification_access_secret_token_{os.environ['environment']}"
    )
    client_secret = get_param(
        f"apple_update_notification_secret_key_{os.environ['environment']}"
    )

    # Authenticate to Twitter
    # auth = tweepy.OAuthHandler(f"{client_id}", f"{client_secret}")
    # auth.set_access_token(f"{access_token}", f"{access_token_secret}")

    # Create API object
    twitter_client = tweepy.Client(consumer_key=client_id, consumer_secret=client_secret, access_token=access_token, access_token_secret=access_token_secret)
    return twitter_client


def create_dynamodb_client():
    """Creates dynamodb client"""
    logger.info("Creating Dynamo client.")
    session = boto3.resource("dynamodb")
    return session
