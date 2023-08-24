"""AWS SDK for Python"""
import sys

sys.path.append("/opt")
import re
import os
import logging
import time
from botocore.exceptions import ClientError
from apple_utils import (
    get_param,
    authenticate_twitter_client
)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main function for lambda function"""

    for record in event['Records']:

        device = record['dynamodb']['Keys']['device']['S']
        release_statement = record['dynamodb']['NewImage']['ReleaseStatement']['S']
        release_version = record['dynamodb']['NewImage']['ReleaseVersion']['S']
        time_created = record['dynamodb']['ApproximateCreationDateTime']
        event_name = record['eventName']
        event_version = record['eventVersion']

        stream_details = {"device": device, "release_version": release_version, "time_created": time_created, "event_name": event_name, "event_version": event_version}

        logger.info(stream_details)

