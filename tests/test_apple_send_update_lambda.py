import pytest
from unittest.mock import patch, MagicMock
from lambdas import apple_send_update as aws


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------
@pytest.fixture
def mock_twitter_client():
    """Mock Tweepy client with create_tweet method."""
    client = MagicMock()
    client.create_tweet.return_value = {"data": {"id": "12345"}}
    return client


@pytest.fixture
def dynamodb_event():
    """Sample DynamoDB stream event containing VisionOS and other devices."""
    return {
        "Records": [
            {
                "eventName": "MODIFY",
                "dynamodb": {
                    "NewImage": {
                        "device": {"S": "visionOS"},
                        "ReleaseStatement": {"S": "visionOS 26.0.1 released!"},
                    }
                },
            },
            {
                "eventName": "MODIFY",
                "dynamodb": {
                    "NewImage": {
                        "device": {"S": "macOS"},
                        "ReleaseStatement": {"S": "macOS 26.0.1 released!"},
                    }
                },
            },
        ]
    }


# -------------------------------------------------------------------------
# Tests for lambda_handler
# -------------------------------------------------------------------------
@patch("lambdas.apple_send_update.authenticate_twitter_client")
@patch("lambdas.apple_send_update.post_tweet")
def test_lambda_handler_success(
    mock_post, mock_auth, dynamodb_event, mock_twitter_client
):
    mock_auth.return_value = mock_twitter_client

    aws.lambda_handler(dynamodb_event, {})

    # Should authenticate once and tweet twice (visionOS + macOS)
    mock_auth.assert_called_once()
    assert mock_post.call_count == 2
    calls = [call.args[1] for call in mock_post.call_args_list]
    assert any("visionOS 26.0.1" in c for c in calls)
    assert any("macOS 26.0.1" in c for c in calls)


@patch(
    "lambdas.apple_send_update.authenticate_twitter_client",
    side_effect=Exception("Auth failed"),
)
def test_lambda_handler_auth_failure(mock_auth, dynamodb_event):
    """If authentication fails, lambda should log and exit without tweeting."""
    aws.lambda_handler(dynamodb_event, {})
    mock_auth.assert_called_once()


@patch("lambdas.apple_send_update.authenticate_twitter_client")
@patch("lambdas.apple_send_update.post_tweet")
def test_lambda_handler_no_records(mock_post, mock_auth):
    """Lambda should handle empty event without errors."""
    aws.lambda_handler({"Records": []}, {})
    mock_auth.assert_called_once()
    mock_post.assert_not_called()


# -------------------------------------------------------------------------
# Tests for post_tweet
# -------------------------------------------------------------------------
def test_post_tweet_success(mock_twitter_client):
    aws.post_tweet(mock_twitter_client, "Sample tweet")
    mock_twitter_client.create_tweet.assert_called_once_with(text="Sample tweet")


def test_post_tweet_exception_handling(mock_twitter_client):
    """If Tweepy raises an error, it should be caught and logged."""
    mock_twitter_client.create_tweet.side_effect = Exception("Twitter error")
    aws.post_tweet(mock_twitter_client, "Bad tweet")
    mock_twitter_client.create_tweet.assert_called_once_with(text="Bad tweet")
