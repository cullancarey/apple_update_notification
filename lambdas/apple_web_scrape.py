import os
import logging
import urllib3
import re

from bs4 import BeautifulSoup
from botocore.exceptions import ClientError

try:
    from .apple_utils import (
        get_device_item,
        create_dynamodb_resource,
        notify_error,
        publish_release_notification,
    )
except ImportError:
    from apple_utils import (
        get_device_item,
        create_dynamodb_resource,
        notify_error,
        publish_release_notification,
    )

# Constants
APPLE_RELEASE_URL = "https://support.apple.com/en-us/100100"
DEVICE_LIST = ["iOS", "macOS", "watchOS", "tvOS", "visionOS"]
DYNAMODB_TABLE_ENV_VAR = "dynamodb_table_name"

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def fetch_apple_release_page(url=APPLE_RELEASE_URL):
    """Fetch the latest Apple releases page."""
    http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=10))
    try:
        response = http.request("GET", url, redirect=True)
        if response.status != 200:
            logger.error(f"Failed to fetch URL {url}. Status code: {response.status}")
            notify_error(
                source="apple_web_scrape",
                error_message="Failed to fetch Apple release page.",
                details={"status_code": response.status, "url": url},
            )
            return None
        return response.data.decode("utf-8", errors="ignore")
    except urllib3.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching Apple release page: {e}")
        notify_error(
            source="apple_web_scrape",
            error_message="HTTP error while fetching Apple release page.",
            details={"exception": str(e), "url": url},
        )
        return None
    except Exception as e:
        logger.error(f"Error fetching Apple release page: {e}", exc_info=True)
        notify_error(
            source="apple_web_scrape",
            error_message="Unexpected error while fetching Apple release page.",
            details={"exception": str(e), "url": url},
        )
        return None


def parse_release_statements(page_content):
    """Parse and return release statements mapped explicitly by device."""
    soup = BeautifulSoup(page_content, "html.parser")

    # Updated: new Apple markup uses <ul class="gb-list"><li><p class="gb-paragraph">...</p></li>
    paragraphs = soup.select("ul.gb-list li.gb-list_item p.gb-paragraph")
    release_statements = {}

    for p in paragraphs:
        text = p.get_text(" ", strip=True).replace("\xa0", " ")
        lower = text.lower()

        if "the latest version" not in lower:
            continue

        # Extract the main sentence up to the version number
        match = re.search(r"The latest version[^.]+?\d+(?:\.\d+)+", text)
        if not match:
            continue

        statement_text = match.group(0).strip()

        # Map each OS explicitly
        if "ios" in lower and "ipados" in lower:
            release_statements["iOS"] = statement_text
        elif "macos" in lower:
            release_statements["macOS"] = statement_text
        elif "watchos" in lower:
            release_statements["watchOS"] = statement_text
        elif "tvos" in lower:
            release_statements["tvOS"] = statement_text
        elif "visionos" in lower:
            release_statements["visionOS"] = statement_text

    # Warn if some expected devices are missing
    missing = [d for d in DEVICE_LIST if d not in release_statements]
    if missing:
        logger.warning(
            f"Incomplete release statements fetched, missing devices: {missing}"
        )

    return release_statements if release_statements else None


def extract_release_versions(release_statements):
    """Extract release versions explicitly by device."""
    releases = {}
    for device, statement in release_statements.items():
        version_match = re.search(r"\b\d+(\.\d+)+\b", statement)
        if version_match:
            releases[device] = version_match.group(0)
        else:
            logger.error(f"Could not extract version from statement: {statement}")

    if len(releases) < len(release_statements):
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

    release_messages = {
        device: f"{release_statements[device]}" for device in release_statements
    }

    releases_dict = {device: release_versions[device] for device in release_versions}
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
        notify_error(
            source="apple_web_scrape",
            error_message="Failed to update DynamoDB release state.",
            details={
                "device": device,
                "release_version": release_version,
                "exception": str(err),
            },
        )
        return False
    else:
        logger.info(
            f"Successfully updated {device} version {release_version} in DynamoDB."
        )
        return True


def format_combined_notification(changed_releases):
    """Build a single SNS email for all release updates found in one scrape."""
    subject = f"Apple release updates: {len(changed_releases)} change(s) detected"
    lines = ["New Apple releases were detected:"]

    for release in changed_releases:
        lines.extend(
            [
                "",
                f"- {release['device']}",
                f"  Version: {release['release_version']}",
                f"  Details: {release['release_statement']}",
            ]
        )

    message = "\n".join(lines)
    return subject, message


def lambda_handler(event, context):
    """AWS Lambda entry-point function."""
    dynamodb_table_name = os.getenv(DYNAMODB_TABLE_ENV_VAR)
    if not dynamodb_table_name:
        logger.error(f"Environment variable '{DYNAMODB_TABLE_ENV_VAR}' is not set.")
        notify_error(
            source="apple_web_scrape",
            error_message="Missing required Lambda environment variable.",
            details={"variable": DYNAMODB_TABLE_ENV_VAR},
        )
        return

    latest_releases = get_latest_releases()

    if not latest_releases:
        logger.error("Failed to retrieve latest releases.")
        notify_error(
            source="apple_web_scrape",
            error_message="Failed to retrieve latest Apple releases.",
        )
        return

    logger.info(f"Latest releases fetched: {latest_releases}")

    dynamodb = create_dynamodb_resource()
    table = dynamodb.Table(dynamodb_table_name)
    changed_releases = []

    for device, latest_version in latest_releases.items():
        if device == "release_statements":
            continue

        existing_item = get_device_item(table=table, device=device)
        existing_version = (
            existing_item.get("ReleaseVersion") if existing_item else None
        )

        if existing_version == latest_version:
            logger.info(f"No update needed for {device}.")
            continue

        release_statement = latest_releases["release_statements"][device]
        updated = update_dynamodb(
            table=table,
            device=device,
            release_version=latest_version,
            release_statement=release_statement,
        )

        if updated:
            changed_releases.append(
                {
                    "device": device,
                    "release_version": latest_version,
                    "release_statement": release_statement,
                }
            )

    if not changed_releases:
        logger.info("No release changes detected.")
        return

    try:
        subject, message = format_combined_notification(changed_releases)
        publish_release_notification(subject, message)
        logger.info(
            "Sent combined release notification for %d updates.", len(changed_releases)
        )
    except Exception as err:
        logger.error(
            "Failed to publish combined release notification: %s", err, exc_info=True
        )
        notify_error(
            source="apple_web_scrape",
            error_message="Failed to publish combined release notification.",
            details={"exception": str(err), "changed_releases": changed_releases},
        )
