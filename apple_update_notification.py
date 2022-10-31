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
    tv_os_msg = f"tvOS release available! \n{release_statements[2]} \n{datetime.now()} \n#tvOS #apple"
    watchOS_msg = f"watchOS release available! \n{release_statements[3]} \n{datetime.now()} \n#watchOS #apple"
    if release_list["iOS"] != db_list["iOS"]:
        # twitter_client.update_status(iOS_msg)
        #   update_item(
        # conn, str(today), str(
        #     release_list['iOS']))
        print("updating iOS item")
        print(iOS_msg)
    else:
        print("no new iOS updates")
    if release_list["macOS"] != db_list["macOS"]:
        # twitter_client.update_status(macOS_msg)
        #   update_item(
        # conn, str(today), str(
        #         release_list['macOS']))
        print("updating macOS item")
        print(macOS_msg)
    else:
        print("no new macOS updates")
    if release_list["tvOS"] != db_list["tvOS"]:
        # twitter_client.update_status(tv_os_msg)
        #   update_item(
        # conn, str(today), str(
        #             release_list['tvOS']))
        print("updating tvOs item")
        print(tv_os_msg)
    else:
        print("no new tvOS updates")
    if release_list["watchOS"] != db_list["watchOS"]:
        # twitter_client.update_status(watchOS_msg)
        #   update_item(
        # conn, str(today), str(
        #                 release_list['watchOS']))
        print("updating watchOS item")
        print(watchOS_msg)
    else:
        print("no new watchOS updates")


def update_item(
    table, rowid, iOS_release, macOS_release, tvOS_release, watchOS_release
):
    """Updates DynamoDB with new release value"""
    try:
        table.update_item(
            Item={
                "RowId": rowid,
                "iOS": iOS_release,
                "macOS": macOS_release,
                "tvOS": tvOS_release,
                "watchOS": watchOS_release,
            }
        )
    except ClientError:
        print(ClientError)
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
                print(x)
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
    # tweet_date = "2022-10-24"

    # Get latest releases in dynamo
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("apple_os_releases")
    dynamo_releases = get_item(table, tweet_date)
    # releases = {'RowId': '2022-10-24', 'macOS': '1', 'tvOS': '16', 'watchOS': '9.1', 'iOS': '16.1'}

    # Check if release is up to date
    print(f"Website list: {releases}")
    print(f"DynamoDB list: {dynamo_releases}")

    # Compares results from apple website and dynamo table
    compare_lists(today, releases, dynamo_releases, table, release_statements)


lambda_handler()
