"""AWS SDK for Python"""
import sys

sys.path.append("/opt")
import urllib3
from bs4 import BeautifulSoup
import re
import os
import logging
import time
from botocore.exceptions import ClientError
from apple_utils import (
    get_item,
    create_dynamodb_client,
)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def compare_lists(today, release_dictionary, db_list, db_table_conn, oldest_item):
    """Compares the releases from the website to what is in DynamoDB
    and updates DynamoDB of the new records if they exist. Also
    tweets about new updates if they exist"""
    difference = {
        k: db_list[k]
        for k in db_list
        if k not in release_dictionary or release_dictionary[k] != db_list[k]
    }
    difference.pop("timestamp")
    difference.pop("ReleaseStatements")
    logger.info(difference)

    device_list = ["iOS", "macOS", "watchOS", "tvOS"]

    if difference:
        for device in device_list:
            if device in difference.keys():
                logger.info(f"Update available for {device}. Updating Dynamo.")
                update_item(table=db_table_conn, timestamp=today, device=device, release_dict=release_dictionary)
            else:
                logger.info(f"No new updates for {device}")
                update_item(table=db_table_conn, timestamp=today, device=device, release_dict=release_dictionary)
        # Delete the oldest item
        logger.info(f"Deleting oldest item {oldest_item}.")
        try:
            db_table_conn.delete_item(
                Key={
                    'timestamp': oldest_item['timestamp']
                }
            )
        except ClientError as err:
            logger.error(f"Error deleting oldest item {oldest_item} with error {err}.")
        logger.info(f"Finished updating releases.")
    else:
        logger.info(f"No updates available at {today}.")


def update_item(table, timestamp, device, release_dict):
    """Updates DynamoDB with new release value"""
    try:
        table.update_item(
            Key={"timestamp": timestamp},
            UpdateExpression=f"SET {device}=:{device},"
            f"ReleaseStatements=:ReleaseStatements",
            ExpressionAttributeValues={
                f":{device}": release_dict[device],
                ":ReleaseStatements": release_dict["release_statements"],
            },
            ReturnValues="UPDATED_NEW",
        )
    except ClientError as err:
        logger.error(f"Exception ocurred updating {device} in DynamoDB: {err}")
    else:
        logger.info(f"Successfully uploaded {device} to dynamodb.")


def get_latest_releases(today):
    """Get latest releases from Apple website"""
    logger.info(f"Getting latest apple releases.")
    http = urllib3.PoolManager()
    page = http.request("GET", "https://support.apple.com/en-us/HT201222")

    soup = BeautifulSoup(page.data, "html.parser")
    results = soup.find_all("li")
    release_statements = []
    for i in results:
        if "The latest version" in i.text:
            s = i.text.replace(" ", " ")
            group = re.search("^.*?[.!?](?:\\s|$)(?!.*?\\))", s)
            group = group.group(0)
            release_statements.append(group)

    iOS_msg = f"iOS release available! \n{release_statements[0]} \n{time.time()} \n#iOS #apple"
    macOS_msg = f"macOS release available! \n{release_statements[1]} \n{time.time()} \n#macOS #apple"
    tvOS_msg = f"tvOS release available! \n{release_statements[2]} \n{time.time()} \n#tvOS #apple"
    watchOS_msg = f"watchOS release available! \n{release_statements[3]} \n{time.time()} \n#watchOS #apple"
    release_messages = {
        "iOS": f"{iOS_msg}",
        "macOS": f"{macOS_msg}",
        "tvOS": f"{tvOS_msg}",
        "watchOS": f"{watchOS_msg}",
    }

    releases = []
    for i in release_statements:
        y = re.findall(r"[\d\.]+", i)
        for x in y:
            if "." in x and len(x) > 1:
                if x[-1] == ".":
                    releases.append(x[0:-1])
                if x[-1].isdigit():
                    releases.append(x)

    releases = {
        "timestamp": today,
        "iOS": releases[0],
        "macOS": releases[1],
        "tvOS": releases[2],
        "watchOS": releases[3],
        "release_statements": release_messages,
    }
    return releases


def lambda_handler(event, context):
    """Main function for lambda function"""

    today = int(time.time())

    releases = get_latest_releases(today=today)

    # Get latest releases in dynamo
    dynamodb = create_dynamodb_client()
    table = dynamodb.Table(os.environ.get("dynamodb_table_name"))
    dynamo_releases, oldest_item = get_item(table=table, today=today)
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
    #             "watchOS": "watchOS release available! \nThe latest version of watchOS is 9.1.  \n2022-11-08 15:59:42.526838 \n#watchOS #apple test",
    #         },
    #     }

    # Check if release is up to date
    logger.info(f"Website list: {releases}")
    logger.info(f"DynamoDB list: {dynamo_releases}")

    # Compares results from apple website and dynamo table
    compare_lists(
        today=today,
        release_dictionary=releases,
        db_list=dynamo_releases,
        db_table_conn=table,
        oldest_item=oldest_item
    )
