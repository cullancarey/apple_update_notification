"""AWS Lambda function to send Apple release notifications based on DynamoDB Streams."""

import os
import logging
from typing import Any, Dict

try:
    from .apple_utils import (
        create_dynamodb_resource,
        notify_error,
        mark_release_notified,
        publish_release_notification,
    )
except ImportError:
    from apple_utils import (
        create_dynamodb_resource,
        notify_error,
        mark_release_notified,
        publish_release_notification,
    )

# -------------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE_ENV_VAR = "dynamodb_table_name"


# -------------------------------------------------------------------------
# Lambda Handler
# -------------------------------------------------------------------------
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Processes DynamoDB stream records and sends any new release updates.
    Invoked automatically by DynamoDB Streams → Lambda event mapping.
    """

    records = event.get("Records", [])

    dynamodb_table_name = os.getenv(DYNAMODB_TABLE_ENV_VAR)
    if not dynamodb_table_name:
        logger.error("Environment variable '%s' is not set.", DYNAMODB_TABLE_ENV_VAR)
        notify_error(
            source="apple_send_update",
            error_message="Missing required Lambda environment variable.",
            details={"variable": DYNAMODB_TABLE_ENV_VAR},
        )
        return {
            "batchItemFailures": [
                {"itemIdentifier": r["eventID"]} for r in records if r.get("eventID")
            ]
        }

    dynamodb = create_dynamodb_resource()
    table = dynamodb.Table(dynamodb_table_name)

    failures = []

    for record in records:
        event_id = record.get("eventID")
        try:
            dynamodb_data = record.get("dynamodb", {})
            if record.get("eventName") != "MODIFY":
                continue

            new_image = dynamodb_data.get("NewImage", {})
            device_name = new_image.get("device", {}).get("S")
            release_version = new_image.get("ReleaseVersion", {}).get("S")
            release_statement = new_image.get("ReleaseStatement", {}).get("S")
            if not release_statement or not release_version or not device_name:
                logger.warning(
                    "Missing required stream fields for event %s, skipping notification.",
                    event_id,
                )
                continue

            if not mark_release_notified(table, device_name, release_version):
                continue

            logger.info(
                "Sending release notification for %s.",
                device_name or "unknown device",
            )
            subject, message = format_notification(
                device_name, release_version, release_statement
            )
            publish_release_notification(subject, message)

        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            notify_error(
                source="apple_send_update",
                error_message="Error processing DynamoDB stream record.",
                details={
                    "event_id": event_id,
                    "exception": str(e),
                },
            )
            if event_id:
                failures.append({"itemIdentifier": event_id})

    logger.info("Lambda execution completed with %d failed records.", len(failures))
    return {"batchItemFailures": failures}


def format_notification(
    device: str, release_version: str, release_statement: str
) -> tuple[str, str]:
    """Return an SNS email subject and body for a given Apple OS release."""
    subject = f"Apple release update: {device} {release_version}"
    message = (
        f"A new Apple release was detected for {device}.\n\n"
        f"Version: {release_version}\n"
        f"Details: {release_statement}\n"
    )
    return subject, message
