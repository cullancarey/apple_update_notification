"""AWS SDK utilities for DynamoDB and SNS notifications."""

import json
import os
import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

# -------------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------
ERROR_ALERT_TOPIC_ENV_VAR = "error_alert_topic_arn"
RELEASE_NOTIFICATION_TOPIC_ENV_VAR = "release_notification_topic_arn"

# -------------------------------------------------------------------------
# Global AWS Session / Config (improves Lambda cold-start performance)
# -------------------------------------------------------------------------
boto_cfg = Config(retries={"max_attempts": 5, "mode": "standard"})
session = boto3.session.Session()

# Global clients reused across invocations
dynamodb_resource = session.resource("dynamodb", config=boto_cfg)
sns_client = session.client("sns", config=boto_cfg)


class DynamoDBItemNotFound(Exception):
    """Raised when a specific item is not found in DynamoDB."""

    pass


# -------------------------------------------------------------------------
# AWS Clients Creation
# -------------------------------------------------------------------------
def create_dynamodb_resource(region_name=None):
    """Creates and returns a DynamoDB resource (region-aware)."""
    if not region_name:
        return dynamodb_resource
    return boto3.resource("dynamodb", region_name=region_name, config=boto_cfg)


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


def publish_release_notification(subject: str, message: str) -> None:
    """Publish a release notification to SNS when a release topic is configured."""
    topic_arn = os.getenv(RELEASE_NOTIFICATION_TOPIC_ENV_VAR)
    if not topic_arn:
        logger.info(
            "Release notification topic is not configured; skipping notification publish."
        )
        return

    try:
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
    except (ClientError, BotoCoreError):
        logger.error("Failed to publish SNS release notification.", exc_info=True)
        raise


def notify_error(source: str, error_message: str, details: dict | None = None) -> None:
    """Publish an error notification to SNS when an alert topic is configured."""
    topic_arn = os.getenv(ERROR_ALERT_TOPIC_ENV_VAR)
    if not topic_arn:
        return

    payload = {
        "source": source,
        "error_message": error_message,
        "details": details or {},
    }

    try:
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=f"Lambda error: {source}",
            Message=json.dumps(payload, default=str),
        )
    except (ClientError, BotoCoreError):
        logger.error("Failed to publish SNS error notification.", exc_info=True)


# -------------------------------------------------------------------------
# Module Exports
# -------------------------------------------------------------------------
__all__ = [
    "create_dynamodb_resource",
    "get_device_item",
    "publish_release_notification",
    "notify_error",
    "DynamoDBItemNotFound",
]
