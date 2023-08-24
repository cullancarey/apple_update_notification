"""module for python aws sdk"""
import boto3
import tweepy
import os
import sys
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


def get_item(table, device_list):
    """Retrieves latest releases item from DynamoDB table"""
    logger.info("Retrieving items from Dynamo.")
    releases = {
    'iOS': None,
    'macOS': None,
    'tvOS': None,
    'watchOS': None,
    'release_statements': {
        'iOS': None,
        'macOS': None,
        'tvOS': None,
        'watchOS': None
            }
            }                   
    for device in device_list:
        try:
            response = table.get_item(Key={"device": device})
        except ClientError as err:
            logger.error(f"Exception ocurred retrieving item from DynamoDB: {err}")
        else:
            if response.get("Item", False):
                logger.info(
                    f"Successfully retrieved item from DynamoDB."
                )
                releases[device] = response["Item"].get('ReleaseVersion')
                releases['release_statements'][device] = response["Item"].get('ReleaseStatement')
            else:
                logger.error(
                    f"Unable to find item from table: {table}. Exiting..."
                )
                sys.exit()
    return releases


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
