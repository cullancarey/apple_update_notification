import sys

sys.path.append("/opt")

import os
import logging
import time
import urllib3
import re

from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from apple_utils import get_item, create_dynamodb_resource

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
        response = http.request("GET", url, redirect=True)
        if response.status != 200:
            logger.error(f"Failed to fetch URL {url}. Status code: {response.status}")
            return None
        return response.data
    except urllib3.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching Apple release page: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}", exc_info=True)
        return None


def parse_release_statements(page_content):
    """Parse and return release statements mapped explicitly by device."""
    soup = BeautifulSoup(page_content, "html.parser")
    results = soup.find_all("li")
    release_statements = {}

    for item in results:
        text = item.get_text(strip=True).replace(" ", " ")
        if "The latest version" in text:
            statement = re.search("^.*?[.!?](?:\\s|$)(?!.*?\\))", text)
            if statement:
                statement_text = statement.group(0)
                statement_lower = statement_text.lower()
                if "ios" in statement_lower and "ipados" in statement_lower:
                    release_statements["iOS"] = statement_text
                elif "macos" in statement_lower:
                    release_statements["macOS"] = statement_text
                elif "watchos" in statement_lower:
                    release_statements["watchOS"] = statement_text
                elif "tvos" in statement_lower:
                    release_statements["tvOS"] = statement_text

    # Verify that all devices have a statement
    missing_devices = [
        device for device in DEVICE_LIST if device not in release_statements
    ]
    if missing_devices:
        logger.error(
            f"Incomplete release statements fetched, missing devices: {missing_devices}"
        )
        return None

    return release_statements


def extract_release_versions(release_statements):
    """Extract release versions explicitly by device."""
    releases = {}
    for device, statement in release_statements.items():
        version_match = re.search(r"\b\d+(\.\d+)+\b", statement)
        if version_match:
            releases[device] = version_match.group(0)
        else:
            logger.warning(f"Could not extract version from statement: {statement}")
            releases[device] = "Unknown"

    if len(releases) < len(DEVICE_LIST):
        logger.error("Incomplete release versions extracted.")
        return None

    return releases


def get_latest_releases():
    """Fetch and parse the latest Apple software releases explicitly by device."""
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
        device: f"{device} release available!\n{release_statements[device]}\n{timestamp}\n#{device} #apple"
        for device in DEVICE_LIST
    }

    releases_dict = {device: release_versions[device] for device in DEVICE_LIST}
    releases_dict["release_statements"] = release_messages

    return releases_dict


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
        logger.error(
            f"Error updating {device} for version {release_version} in DynamoDB: {err}"
        )
        return False
    else:
        logger.info(
            f"Successfully updated {device} version {release_version} in DynamoDB."
        )
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
    # latest_releases = {
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
    logger.info(f"Latest releases fetched: {latest_releases}")

    dynamodb = create_dynamodb_resource()
    table = dynamodb.Table(dynamodb_table_name)

    dynamo_releases = get_item(table=table, device_list=DEVICE_LIST)
    if not dynamo_releases:
        logger.warning("No existing data found in DynamoDB; populating fresh data.")
        dynamo_releases = {}

    compare_and_update_releases(latest_releases, dynamo_releases, table)
