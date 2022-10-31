"""AWS SDK for Python"""
import boto3
import urllib3
import tweepy
from bs4 import BeautifulSoup
import re
from datetime import datetime
from botocore.exceptions import ClientError


def compare_lists(today, release_list, db_list, conn, release_statements):
    """Compares the releases from the website to what is in DynamoDB
    and updates DynamoDB of the new records if they exist. Also
    tweets about new updates if they exist"""
    iOS_msg = f"iOS release available! \n{release_statements[0]} \n{datetime.now()} \n#iOS #apple"
    macOS_msg = f"macOS release available! \n{release_statements[1]} \n{datetime.now()} \n#macOS #apple"
    tvOS_msg = f"tvOS release available! \n{release_statements[2]} \n{datetime.now()} \n#tvOS #apple"
    watchOS_msg = f"watchOS release available! \n{release_statements[3]} \n{datetime.now()} \n#watchOS #apple"
    if (not db_list.get("iOS", False)) or (release_list["iOS"] == db_list.get("iOS")):
        print("no new iOS updates")
    else:
        if release_list["iOS"] != db_list.get("iOS"):
            print("updating iOS item")
            update_item(conn, str(today), "iOS", release_list["iOS"])
            print(iOS_msg)
            # twitter_client.update_status(iOS_msg)
    if (not db_list.get("macOS", False)) or (
        release_list["macOS"] == db_list.get("macOS")
    ):
        print("no new macOS updates")
    else:
        if release_list["macOS"] != db_list.get("macOS"):
            print("updating macOS item")
            update_item(conn, str(today), "macOS", release_list["macOS"])
            print(macOS_msg)
            # twitter_client.update_status(macOS_msg)
    if (not db_list.get("tvOS", False)) or (
        release_list["tvOS"] == db_list.get("tvOS")
    ):
        print("no new tvOS updates")
    else:
        if release_list["tvOS"] != db_list.get("tvOS"):
            print("updating tvOS item")
            update_item(conn, str(today), "tvOS", release_list["tvOS"])
            print(tvOS_msg)
            # twitter_client.update_status(tvOS_msg)
    if (not db_list.get("watchOS", False)) or (
        release_list["watchOS"] == db_list.get("watchOS")
    ):
        print("no new watchOS updates")
    else:
        if release_list["watchOS"] != db_list.get("watchOS"):
            print("updating watchOS item")
            update_item(conn, str(today), "watchOS", release_list["watchOS"])
            print(watchOS_msg)
            # twitter_client.update_status(watchOS_msg)


def update_item(table, rowid, device, release_dict):
    """Updates DynamoDB with new release value"""
    try:
        updated = table.update_item(
            Key={"RowId": rowid},
            UpdateExpression=f"SET {device}=:{device}",
            ExpressionAttributeValues={f":{device}": release_dict},
            ReturnValues="UPDATED_NEW",
        )
        print(f"Updated releases: {updated.get('Attributes', 'No new releases.')}")
    except ClientError as err:
        print(f"Exception ocurred updating item in DynamoDB: {err}")
    else:
        print("Successfully uploaded item to dynamodb.")


def get_item(table, date):
    """Retrieves latest releases item from DynamoDB table"""
    try:
        response = table.get_item(Key={"RowId": date})
    except ClientError as err:
        print(f"Exception ocurred retrieving item from DynamoDB: {err}")
    else:
        print(f"Successfully retrieved item from DynamoDB: {response['Item']}")

    return response["Item"]


def get_param(param):
    """Retrieves parameter secrets from Parameter Store"""
    client = boto3.client("ssm")
    response = client.get_parameter(Name=param, WithDecryption=True)
    return response["Parameter"]["Value"]


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
    }
    return release_statements, releases


def authenticate_twitter_client():
    """Gets authenticated session from Twitter"""
    CLIENT_ID = get_param("apple_update_notification_api_key")
    ACCESS_TOKEN = get_param("apple_update_notification_twitter_access_token")
    ACCESS_TOKEN_SECRET = get_param("apple_update_notification_access_secret_token")
    CLIENT_SECRET = get_param("apple_update_notification_secret_key")

    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(f"{CLIENT_ID}", f"{CLIENT_SECRET}")
    auth.set_access_token(f"{ACCESS_TOKEN}", f"{ACCESS_TOKEN_SECRET}")

    # Create API object
    twitter_client = tweepy.API(auth)
    return twitter_client


def lambda_handler():
    """Main function for lambda function"""

    today = datetime.now().strftime("%Y-%m-%d")
    release_statements, releases = get_latest_releases(today)

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
    # tweet_date = "2022-10-31"

    # Get latest releases in dynamo
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("apple_os_releases")
    dynamo_releases = get_item(table, tweet_date)
    # releases = {
    #     "RowId": "2022-10-24",
    #     "macOS": "10",
    #     "tvOS": "16",
    #     "watchOS": "9.2",
    #     "iOS": "16.0",
    # }

    # Check if release is up to date
    print(f"Website list: {releases}")
    print(f"DynamoDB list: {dynamo_releases}")

    # Compares results from apple website and dynamo table
    compare_lists(today, releases, dynamo_releases, table, release_statements)
