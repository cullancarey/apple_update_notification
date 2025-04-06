import sys

sys.path.append("/opt")
import os
import logging
import time
import urllib3
import re

from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from apple_utils import get_item, create_dynamodb_client

# Constants
APPLE_RELEASE_URL = "https://support.apple.com/en-us/HT201222"
DEVICE_LIST = ["iOS", "macOS", "watchOS", "tvOS"]
DYNAMODB_TABLE_ENV_VAR = "dynamodb_table_name"

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def fetch_apple_release_page(url=APPLE_RELEASE_URL):
    """Fetch the latest Apple releases page."""
    http = urllib3.PoolManager()
    try:
        response = http.request("GET", url)
        response.raise_for_status()
        return response.data
    except urllib3.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching Apple release page: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        return None


def parse_release_statements(page_content):
    """Parse and return release statements from the fetched HTML."""
    soup = BeautifulSoup(page_content, "html.parser")
    results = soup.find_all("li")
    release_statements = []

    for item in results:
        text = item.get_text(strip=True).replace(" ", " ")
        if "The latest version" in text:
            match = re.search("^.*?[.!?](?:\\s|$)(?!.*?\\))", text)
            if match:
                release_statements.append(match.group(0))

    if len(release_statements) < len(DEVICE_LIST):
        logger.error("Incomplete release statements fetched.")
        return None

    return release_statements


def extract_release_versions(release_statements):
    """Extract and return release versions from release statements."""
    releases = []
    for statement in release_statements:
        version_match = re.search(r"\b\d+(\.\d+)+\b", statement)
        if version_match:
            releases.append(version_match.group(0))
        else:
            logger.warning(f"Could not extract version from statement: {statement}")
            releases.append("Unknown")

    if len(releases) < len(DEVICE_LIST):
        logger.error("Incomplete release versions extracted.")
        return None

    return releases


def get_latest_releases():
    """Fetch and parse the latest Apple software releases."""
    page_content = fetch_apple_release_page()
    if not page_content:
        return None

    release_statements = parse_release_statements(page_content)
    if not release_statements:
        return None

    release_versions = extract_release_versions(release_statements)
    if not release_versions:
        return None

    timestamp = int(time.time())
    release_messages = {
        device: f"{device} release available!\n{statement}\n{timestamp}\n#{device} #apple"
        for device, statement in zip(DEVICE_LIST, release_statements)
    }

    return {
        device: version for device, version in zip(DEVICE_LIST, release_versions)
    } | {"release_statements": release_messages}


def update_dynamodb(table, device, release_version, release_statement):
    """Update DynamoDB with new release information."""
    logger.info(f"Updating DynamoDB entry for {device}.")
    try:
        table.update_item(
            Key={"device": device},
            UpdateExpression="SET ReleaseVersion=:version, ReleaseStatement=:statement",
            ExpressionAttributeValues={
                ":version": release_version,
                ":statement": release_statement,
            },
            ReturnValues="UPDATED_NEW",
        )
    except ClientError as err:
        logger.error(f"Error updating {device} in DynamoDB: {err}")
        return False
    else:
        logger.info(f"Successfully updated {device} in DynamoDB.")
        return True


def compare_and_update_releases(latest_releases, dynamo_releases, table):
    """Compare and update releases in DynamoDB if needed."""
    updates_needed = {
        device: latest_releases[device]
        for device in DEVICE_LIST
        if device not in dynamo_releases
        or latest_releases[device] != dynamo_releases[device]
    }

    if not updates_needed:
        logger.info("No updates available.")
        return

    for device in updates_needed:
        update_dynamodb(
            table=table,
            device=device,
            release_version=latest_releases[device],
            release_statement=latest_releases["release_statements"][device],
        )

    logger.info("Completed DynamoDB updates.")


def lambda_handler(event, context):
    """AWS Lambda entry-point function."""
    dynamodb_table_name = os.getenv(DYNAMODB_TABLE_ENV_VAR)
    if not dynamodb_table_name:
        logger.error(f"Environment variable '{DYNAMODB_TABLE_ENV_VAR}' is not set.")
        return

    latest_releases = get_latest_releases()
    if not latest_releases:
        logger.error("Failed to retrieve latest releases.")
        return
    # releases = {
    #         "timestamp": today,
    #         "macOS": "13.5.1",
    #         "tvOS": "16.6",
    #         "watchOS": "9.6.1",
    #         "iOS": "16.6",
    #         "release_statements": {
    #             "iOS": "iOS release available! \nThe latest version of iOS is 16.1.  \n2022-11-08 15:59:42.526826 \n#iOS #apple",
    #             "macOS": "macOS release available! \nThe latest version of macOS is 13.  \n2022-11-08 15:59:42.526835 \n#macOS #apple",
    #             "tvOS": "tvOS release available! \nThe latest version of tvOS is 16.1.  \n2022-11-08 15:59:42.526836 \n#tvOS #apple",
    #             "watchOS": "watchOS release available! \nThe latest version of watchOS is 9.1.  \n2022-11-08 15:59:42.526838 \n#watchOS #apple",
    #         },
    #     }

    dynamodb = create_dynamodb_client()
    table = dynamodb.Table(dynamodb_table_name)

    dynamo_releases = get_item(table=table, device_list=DEVICE_LIST)
    if not dynamo_releases:
        logger.warning("No existing data found in DynamoDB; populating fresh data.")
        dynamo_releases = {}

    compare_and_update_releases(latest_releases, dynamo_releases, table)
