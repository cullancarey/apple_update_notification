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
                "eventID": "evt-1",
                "eventName": "MODIFY",
                "dynamodb": {
                    "NewImage": {
                        "device": {"S": "visionOS"},
                        "ReleaseVersion": {"S": "26.0.1"},
                        "ReleaseStatement": {"S": "visionOS 26.0.1 released!"},
                    }
                },
            },
            {
                "eventID": "evt-2",
                "eventName": "MODIFY",
                "dynamodb": {
                    "NewImage": {
                        "device": {"S": "macOS"},
                        "ReleaseVersion": {"S": "26.0.1"},
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
@patch("lambdas.apple_send_update.mark_tweet_posted", return_value=True)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
def test_lambda_handler_success(
    mock_dynamodb_resource,
    mock_mark_tweet_posted,
    mock_post,
    mock_auth,
    dynamodb_event,
    mock_twitter_client,
):
    mock_table = MagicMock()
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    mock_dynamodb_resource.return_value = mock_dynamodb
    mock_auth.return_value = mock_twitter_client

    with patch.dict("os.environ", {"dynamodb_table_name": "table"}):
        result = aws.lambda_handler(dynamodb_event, {})

    # Should authenticate once and tweet twice (visionOS + macOS)
    mock_auth.assert_called_once()
    assert mock_post.call_count == 2
    assert result == {"batchItemFailures": []}
    calls = [call.args[1] for call in mock_post.call_args_list]
    assert any("visionOS 26.0.1" in c for c in calls)
    assert any("macOS 26.0.1" in c for c in calls)


@patch(
    "lambdas.apple_send_update.authenticate_twitter_client",
    side_effect=Exception("Auth failed"),
)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
@patch("lambdas.apple_send_update.notify_error")
def test_lambda_handler_auth_failure(
    mock_notify,
    mock_dynamodb_resource,
    mock_auth,
    dynamodb_event,
):
    """If authentication fails, lambda should log and exit without tweeting."""
    mock_dynamodb_resource.return_value = MagicMock()
    with patch.dict("os.environ", {"dynamodb_table_name": "table"}):
        result = aws.lambda_handler(dynamodb_event, {})
    mock_auth.assert_called_once()
    assert len(result["batchItemFailures"]) == 2
    mock_notify.assert_called_once()


@patch("lambdas.apple_send_update.authenticate_twitter_client")
@patch("lambdas.apple_send_update.post_tweet")
@patch("lambdas.apple_send_update.mark_tweet_posted", return_value=True)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
def test_lambda_handler_no_records(
    mock_dynamodb_resource, mock_mark_tweet_posted, mock_post, mock_auth
):
    """Lambda should handle empty event without errors."""
    mock_dynamodb_resource.return_value = MagicMock()
    with patch.dict("os.environ", {"dynamodb_table_name": "table"}):
        result = aws.lambda_handler({"Records": []}, {})
    mock_auth.assert_called_once()
    mock_post.assert_not_called()
    assert result == {"batchItemFailures": []}


@patch("lambdas.apple_send_update.authenticate_twitter_client")
@patch("lambdas.apple_send_update.post_tweet")
@patch("lambdas.apple_send_update.mark_tweet_posted", return_value=False)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
def test_lambda_handler_skips_duplicate_event(
    mock_dynamodb_resource,
    mock_mark_tweet_posted,
    mock_post,
    mock_auth,
    dynamodb_event,
    mock_twitter_client,
):
    mock_dynamodb_resource.return_value = MagicMock()
    mock_auth.return_value = mock_twitter_client

    with patch.dict("os.environ", {"dynamodb_table_name": "table"}):
        result = aws.lambda_handler(dynamodb_event, {})

    mock_post.assert_not_called()
    assert result == {"batchItemFailures": []}


# -------------------------------------------------------------------------
# Tests for post_tweet
# -------------------------------------------------------------------------
def test_post_tweet_success(mock_twitter_client):
    aws.post_tweet(mock_twitter_client, "Sample tweet")
    mock_twitter_client.create_tweet.assert_called_once_with(text="Sample tweet")


def test_post_tweet_exception_handling(mock_twitter_client):
    """If Tweepy raises an error, it should bubble up for stream retry handling."""
    mock_twitter_client.create_tweet.side_effect = Exception("Twitter error")
    with pytest.raises(Exception, match="Twitter error"):
        aws.post_tweet(mock_twitter_client, "Bad tweet")
    mock_twitter_client.create_tweet.assert_called_once_with(text="Bad tweet")
