"""module for python aws sdk"""
import boto3
import tweepy
from botocore.exceptions import ClientError


def get_param(param):
    """Retrieves parameter secrets from Parameter Store"""
    client = boto3.client("ssm")
    response = client.get_parameter(Name=param, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_item(table, date):
    """Retrieves latest releases item from DynamoDB table"""
    try:
        response = table.get_item(Key={"RowId": date})
    except ClientError as err:
        print(f"Exception ocurred retrieving item from DynamoDB: {err}")
    else:
        print(f"Successfully retrieved item from DynamoDB: {response['Item']}")

    return response["Item"]


def authenticate_twitter_client():
    """Gets authenticated session from Twitter"""
    client_id = get_param("apple_update_notification_api_key")
    access_token = get_param("apple_update_notification_twitter_access_token")
    access_token_secret = get_param("apple_update_notification_access_secret_token")
    client_secret = get_param("apple_update_notification_secret_key")

    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(f"{client_id}", f"{client_secret}")
    auth.set_access_token(f"{access_token}", f"{access_token_secret}")

    # Create API object
    twitter_client = tweepy.API(auth)
    return twitter_client


def create_dynamodb_client():
    """Creates dynamodb client"""
    session = boto3.resource("dynamodb")
    return session
