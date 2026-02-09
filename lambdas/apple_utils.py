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

# -------------------------------------------------------------------------
# Global AWS Session / Config (improves Lambda cold-start performance)
# -------------------------------------------------------------------------
boto_cfg = Config(retries={"max_attempts": 5, "mode": "standard"})
session = boto3.session.Session()

# Global clients reused across invocations
ssm_client = session.client("ssm", config=boto_cfg)
dynamodb_resource = session.resource("dynamodb", config=boto_cfg)


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
def load_twitter_secrets(region_name=None):
    param_names = [
        f"{PARAMETER_PREFIX}_api_key",
        f"{PARAMETER_PREFIX}_secret_key",
        f"{PARAMETER_PREFIX}_twitter_access_token",
        f"{PARAMETER_PREFIX}_access_secret_token",
    ]

    client = create_ssm_client(region_name)

    try:
        response = client.get_parameters(
            Names=param_names,
            WithDecryption=True,
        )
    except (ClientError, BotoCoreError) as e:
        logger.error("Failed to load Twitter secrets", exc_info=True)
        raise ParameterRetrievalError("Failed to load Twitter secrets") from e

    values = {p["Name"]: p["Value"] for p in response.get("Parameters", [])}

    # Optional: enforce contract loudly
    missing = set(param_names) - values.keys()
    if missing:
        raise ParameterRetrievalError(f"Missing parameters: {missing}")

    return values


# -------------------------------------------------------------------------
# DynamoDB Interaction
# -------------------------------------------------------------------------
def get_device_item(table, device: str):
    """
    Retrieves the release data for a single device from DynamoDB.
    Returns the item dict or None if not found.
    """
    try:
        response = table.get_item(Key={"device": device})
        return response.get("Item")
    except ClientError as err:
        logger.error(
            f"Error retrieving item for device '{device}': {err}", exc_info=True
        )
        raise DynamoDBItemNotFound(
            f"Failed to retrieve item for device '{device}'"
        ) from err


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

    secrets = load_twitter_secrets(region_name=region_name)

    try:
        twitter_client = tweepy.Client(
            consumer_key=secrets[f"{PARAMETER_PREFIX}_api_key"],
            consumer_secret=secrets[f"{PARAMETER_PREFIX}_secret_key"],
            access_token=secrets[f"{PARAMETER_PREFIX}_twitter_access_token"],
            access_token_secret=secrets[f"{PARAMETER_PREFIX}_access_secret_token"],
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
    "get_device_item",
    "authenticate_twitter_client",
    "ParameterRetrievalError",
    "DynamoDBItemNotFound",
]
