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

    logger.info(event)
