"""AWS SDK utilities for Parameter Store, DynamoDB, and Twitter interactions."""

import logging
import boto3
import tweepy
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from tweepy.errors import TweepyException

# -------------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------
PARAMETER_PREFIX = "apple_update_notification"
DEVICE_LIST = ["iOS", "macOS", "watchOS", "tvOS"]

# -------------------------------------------------------------------------
# Global AWS Session / Config (improves Lambda cold-start performance)
# -------------------------------------------------------------------------
boto_cfg = Config(retries={"max_attempts": 5, "mode": "standard"})
session = boto3.session.Session()

# Global clients reused across invocations
ssm_client = session.client("ssm", config=boto_cfg)
dynamodb_resource = session.resource("dynamodb", config=boto_cfg)

# Cache Parameter Store lookups within a single invocation
_param_cache = {}


# -------------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------------
class ParameterRetrievalError(Exception):
    """Raised when a Parameter Store retrieval fails."""

    pass


class DynamoDBItemNotFound(Exception):
    """Raised when a specific item is not found in DynamoDB."""

    pass


# -------------------------------------------------------------------------
# AWS Clients Creation
# -------------------------------------------------------------------------
def create_ssm_client(region_name=None):
    """Creates and returns an SSM client (region-aware)."""
    if not region_name:
        return ssm_client
    return boto3.client("ssm", region_name=region_name, config=boto_cfg)


def create_dynamodb_resource(region_name=None):
    """Creates and returns a DynamoDB resource (region-aware)."""
    if not region_name:
        return dynamodb_resource
    return boto3.resource("dynamodb", region_name=region_name, config=boto_cfg)


# -------------------------------------------------------------------------
# Parameter Store Interaction
# -------------------------------------------------------------------------
def get_param(param_name, region_name=None):
    """
    Retrieves a parameter value from AWS Parameter Store.
    Caches the result per Lambda invocation to reduce latency.
    """
    if param_name in _param_cache:
        return _param_cache[param_name]

    logger.info(f"Retrieving parameter: {param_name}")
    client = create_ssm_client(region_name)

    try:
        response = client.get_parameter(Name=param_name, WithDecryption=True)
        value = response["Parameter"]["Value"]
        _param_cache[param_name] = value
        logger.info(f"Successfully retrieved parameter: {param_name}")
        return value
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error retrieving parameter '{param_name}': {e}", exc_info=True)
        raise ParameterRetrievalError(
            f"Failed to retrieve parameter '{param_name}'"
        ) from e


# -------------------------------------------------------------------------
# DynamoDB Interaction
# -------------------------------------------------------------------------
def get_item(table, device_list=DEVICE_LIST):
    """
    Retrieves the latest releases for devices from DynamoDB.
    Returns a dictionary of devices and their release data.
    """
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
        except ClientError as err:
            logger.error(
                f"Error retrieving item for device '{device}': {err}", exc_info=True
            )
            raise DynamoDBItemNotFound(
                f"Failed to retrieve item for device '{device}'"
            ) from err

    return releases


# -------------------------------------------------------------------------
# Twitter Client Authentication
# -------------------------------------------------------------------------
def authenticate_twitter_client(region_name=None):
    """
    Authenticates and returns a Tweepy Twitter client.
    Requires parameters stored in AWS SSM Parameter Store:
    - apple_update_notification_api_key
    - apple_update_notification_secret_key
    - apple_update_notification_twitter_access_token
    - apple_update_notification_access_secret_token
    """
    logger.info("Authenticating Twitter client.")

    try:
        twitter_client = tweepy.Client(
            consumer_key=get_param(f"{PARAMETER_PREFIX}_api_key", region_name),
            consumer_secret=get_param(f"{PARAMETER_PREFIX}_secret_key", region_name),
            access_token=get_param(
                f"{PARAMETER_PREFIX}_twitter_access_token", region_name
            ),
            access_token_secret=get_param(
                f"{PARAMETER_PREFIX}_access_secret_token", region_name
            ),
        )
        logger.info("Successfully authenticated Twitter client.")
        return twitter_client
    except TweepyException as e:
        logger.error(f"Tweepy authentication failed: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during Twitter authentication: {e}", exc_info=True
        )
        raise


# -------------------------------------------------------------------------
# Module Exports
# -------------------------------------------------------------------------
__all__ = [
    "create_ssm_client",
    "create_dynamodb_resource",
    "get_param",
    "get_item",
    "authenticate_twitter_client",
    "ParameterRetrievalError",
    "DynamoDBItemNotFound",
]
