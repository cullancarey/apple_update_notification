"""AWS SDK for Python"""
import urllib3
from bs4 import BeautifulSoup
import re
from datetime import datetime
from botocore.exceptions import ClientError
from apple_utils import (
    authenticate_twitter_client,
    get_item,
    create_dynamodb_client,
)


def compare_lists(today, release_dictionary, db_list, db_table_conn, twitter_conn):
    """Compares the releases from the website to what is in DynamoDB
    and updates DynamoDB of the new records if they exist. Also
    tweets about new updates if they exist"""
    print(twitter_conn)
    print(today)
    print(db_table_conn)
    difference = {
        k: db_list[k]
        for k in db_list
        if k not in release_dictionary or release_dictionary[k] != db_list[k]
    }
    print(f"difference: {difference}")
    if (not db_list.get("iOS", False)) or (
        release_dictionary["iOS"] == db_list.get("iOS")
    ):
        update_item(db_table_conn, str(today), "iOS", release_dictionary)
        print("no new iOS updates")
    else:
        if release_dictionary["iOS"] != db_list.get("iOS"):
            print("updating iOS item")
            update_item(db_table_conn, str(today), "iOS", release_dictionary)
            print(release_dictionary["release_statements"]["iOS"])
            # twitter_conn.update_status(iOS_msg)
    if (not db_list.get("macOS", False)) or (
        release_dictionary["macOS"] == db_list.get("macOS")
    ):
        update_item(db_table_conn, str(today), "macOS", release_dictionary)
        print("no new macOS updates")
    else:
        if release_dictionary["macOS"] != db_list.get("macOS"):
            print("updating macOS item")
            update_item(db_table_conn, str(today), "macOS", release_dictionary)
            print(release_dictionary["release_statements"]["macOS"])
            # twitter_conn.update_status(macOS_msg)
    if (not db_list.get("tvOS", False)) or (
        release_dictionary["tvOS"] == db_list.get("tvOS")
    ):
        update_item(db_table_conn, str(today), "tvOS", release_dictionary)
        print("no new tvOS updates")
    else:
        if release_dictionary["tvOS"] != db_list.get("tvOS"):
            print("updating tvOS item")
            update_item(db_table_conn, str(today), "tvOS", release_dictionary)
            print(release_dictionary["release_statements"]["tvOS"])
            # twitter_conn.update_status(tvOS_msg)
    if (not db_list.get("watchOS", False)) or (
        release_dictionary["watchOS"] == db_list.get("watchOS")
    ):
        update_item(db_table_conn, str(today), "watchOS", release_dictionary)
        print("no new watchOS updates")
    else:
        if release_dictionary["watchOS"] != db_list.get("watchOS"):
            print("updating watchOS item")
            update_item(db_table_conn, str(today), "watchOS", release_dictionary)
            print(release_dictionary["release_statements"]["watchOS"])
            # twitter_conn.update_status(watchOS_msg)


def update_item(table, rowid, device, release_dict):
    """Updates DynamoDB with new release value"""
    try:
        table.update_item(
            Key={"RowId": rowid},
            UpdateExpression=f"SET {device}=:{device},"
            f"ReleaseStatements=:ReleaseStatements",
            ExpressionAttributeValues={
                f":{device}": release_dict[device],
                ":ReleaseStatements": release_dict["release_statements"],
            },
            ReturnValues="UPDATED_NEW",
        )
    except ClientError as err:
        print(f"Exception ocurred updating item in DynamoDB: {err}")
    else:
        # print(f"Updated releases: {updated.get('Attributes', 'No new releases.')}")
        print("Successfully uploaded item to dynamodb.")


def get_latest_releases(today):
    """Get latest releases from Apple website"""
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

    iOS_msg = f"iOS release available! \n{release_statements[0]} \n{datetime.now()} \n#iOS #apple"
    macOS_msg = f"macOS release available! \n{release_statements[1]} \n{datetime.now()} \n#macOS #apple"
    tvOS_msg = f"tvOS release available! \n{release_statements[2]} \n{datetime.now()} \n#tvOS #apple"
    watchOS_msg = f"watchOS release available! \n{release_statements[3]} \n{datetime.now()} \n#watchOS #apple"
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
        "RowId": today,
        "iOS": releases[0],
        "macOS": releases[1],
        "tvOS": releases[2],
        "watchOS": releases[3],
        "release_statements": release_messages,
    }
    return releases


def lambda_handler():
    """Main function for lambda function"""

    today = datetime.now().strftime("%Y-%m-%d")

    releases = get_latest_releases(today)

    twitter_client = authenticate_twitter_client()

    # Look for date in last tweet to ensure we don't tweet more than once for an update
    username = "UpdateApple_"
    tweets_list = twitter_client.user_timeline(screen_name=username, count=1)
    tweet = tweets_list[0]
    tweet_date_from_twitter = str(tweet.created_at)
    tweet_date = re.search(
        "([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))", tweet_date_from_twitter
    )
    tweet_date = tweet_date.group(0)
    print(f"tweet date: {tweet_date}")
    # TEST TWEET DATE
    tweet_date = "2022-12-15"
    # TEST TODAY DATE
    today = "2022-12-17"

    # Get latest releases in dynamo
    dynamodb = create_dynamodb_client()
    table = dynamodb.Table("apple_os_releases")
    dynamo_releases = get_item(table, tweet_date)
    releases = {
        "RowId": today,
        "macOS": "12",
        "tvOS": "12",
        "watchOS": "9.2",
        "iOS": "16.1.2",
        "release_statements": {
            "iOS": "iOS release available! \nThe latest version of iOS is 16.1.  \n2022-11-08 15:59:42.526826 \n#iOS #apple",
            "macOS": "macOS release available! \nThe latest version of macOS is 13.  \n2022-11-08 15:59:42.526835 \n#macOS #apple",
            "tvOS": "tvOS release available! \nThe latest version of tvOS is 16.1.  \n2022-11-08 15:59:42.526836 \n#tvOS #apple",
            "watchOS": "watchOS release available! \nThe latest version of watchOS is 9.1.  \n2022-11-08 15:59:42.526838 \n#watchOS #apple",
        },
    }

    # Check if release is up to date
    print(f"Website list: {releases}")
    print(f"DynamoDB list: {dynamo_releases}")

    # Compares results from apple website and dynamo table
    compare_lists(today, releases, dynamo_releases, table, twitter_client)


lambda_handler()
