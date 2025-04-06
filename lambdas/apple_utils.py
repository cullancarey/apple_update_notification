"""AWS SDK Module for Parameter Store, DynamoDB, and Twitter interactions"""

import boto3
import tweepy
import logging
from botocore.exceptions import ClientError, BotoCoreError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
PARAMETER_PREFIX = "apple_update_notification"
DEVICE_LIST = ["iOS", "macOS", "watchOS", "tvOS"]


# Custom Exceptions
class ParameterRetrievalError(Exception):
    pass


class DynamoDBItemNotFound(Exception):
    pass


# AWS Clients Creation
def create_ssm_client(region_name=None):
    """Creates and returns an SSM client"""
    logger.info("Creating SSM client.")
    return boto3.client("ssm", region_name=region_name)


def create_dynamodb_resource(region_name=None):
    """Creates and returns a DynamoDB resource"""
    logger.info("Creating DynamoDB resource.")
    return boto3.resource("dynamodb", region_name=region_name)


# Parameter Store Interaction
def get_param(param_name, region_name=None):
    """Retrieves parameter value from AWS Parameter Store"""
    logger.info(f"Retrieving parameter: {param_name}")
    ssm_client = create_ssm_client(region_name)

    try:
        response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
        value = response["Parameter"]["Value"]
        logger.info(f"Successfully retrieved parameter: {param_name}")
        return value
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error retrieving parameter '{param_name}': {e}")
        raise ParameterRetrievalError(
            f"Failed to retrieve parameter '{param_name}'"
        ) from e


# DynamoDB Interaction
def get_item(table, device_list=DEVICE_LIST):
    """Retrieves latest releases for devices from DynamoDB"""
    logger.info("Retrieving device release items from DynamoDB.")
    releases = {device: None for device in device_list}
    releases["release_statements"] = {device: None for device in device_list}

    for device in device_list:
        try:
            response = table.get_item(Key={"device": device})
            item = response.get("Item")
            if item:
                releases[device] = item.get("ReleaseVersion")
                releases["release_statements"][device] = item.get("ReleaseStatement")
                logger.info(f"Retrieved item for device '{device}'.")
            else:
                logger.warning(f"No entry found in DynamoDB for device '{device}'.")
                raise DynamoDBItemNotFound(
                    f"No item found for device '{device}' in DynamoDB."
                )
        except ClientError as err:
            logger.error(f"Error retrieving item for device '{device}': {err}")
            raise DynamoDBItemNotFound(
                f"Failed to retrieve item for device '{device}'"
            ) from err

    return releases


# Twitter Client Authentication
def authenticate_twitter_client(region_name=None):
    """Authenticates and returns a Tweepy Twitter client"""
    logger.info("Authenticating Twitter client.")

    api_key = get_param(f"{PARAMETER_PREFIX}_api_key", region_name)
    api_secret_key = get_param(f"{PARAMETER_PREFIX}_secret_key", region_name)
    access_token = get_param(f"{PARAMETER_PREFIX}_twitter_access_token", region_name)
    access_token_secret = get_param(
        f"{PARAMETER_PREFIX}_access_secret_token", region_name
    )

    try:
        twitter_client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret_key,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        logger.info("Successfully authenticated Twitter client.")
        return twitter_client
    except Exception as e:
        logger.error(f"Error authenticating Twitter client: {e}")
        raise
