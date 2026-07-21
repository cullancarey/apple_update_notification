import pytest
from unittest.mock import patch, MagicMock
from lambdas import apple_send_update as aws


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------
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
@patch("lambdas.apple_send_update.publish_release_notification")
@patch("lambdas.apple_send_update.mark_release_notified", return_value=True)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
def test_lambda_handler_success(
    mock_dynamodb_resource,
    mock_mark_release_notified,
    mock_publish_release_notification,
    dynamodb_event,
):
    mock_table = MagicMock()
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    mock_dynamodb_resource.return_value = mock_dynamodb

    with patch.dict(
        "os.environ",
        {
            "dynamodb_table_name": "table",
            "release_notification_topic_arn": "arn:aws:sns:us-east-2:123456789012:release-updates",
        },
    ):
        result = aws.lambda_handler(dynamodb_event, {})

    assert mock_publish_release_notification.call_count == 2
    assert result == {"batchItemFailures": []}
    subjects = [
        call.args[0] for call in mock_publish_release_notification.call_args_list
    ]
    assert any("visionOS 26.0.1" in subject for subject in subjects)
    assert any("macOS 26.0.1" in subject for subject in subjects)


@patch("lambdas.apple_send_update.create_dynamodb_resource")
@patch("lambdas.apple_send_update.notify_error")
@patch(
    "lambdas.apple_send_update.publish_release_notification",
    side_effect=Exception("Publish failed"),
)
@patch("lambdas.apple_send_update.mark_release_notified", return_value=True)
def test_lambda_handler_publish_failure(
    mock_mark_release_notified,
    mock_publish_release_notification,
    mock_notify,
    mock_dynamodb_resource,
    dynamodb_event,
):
    """If release publishing fails, lambda should report the failed records."""
    mock_dynamodb_resource.return_value = MagicMock()
    with patch.dict(
        "os.environ",
        {
            "dynamodb_table_name": "table",
            "release_notification_topic_arn": "arn:aws:sns:us-east-2:123456789012:release-updates",
        },
    ):
        result = aws.lambda_handler(dynamodb_event, {})

    assert len(result["batchItemFailures"]) == 2
    assert mock_notify.call_count == 2


@patch("lambdas.apple_send_update.publish_release_notification")
@patch("lambdas.apple_send_update.mark_release_notified", return_value=True)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
def test_lambda_handler_no_records(
    mock_dynamodb_resource,
    mock_mark_release_notified,
    mock_publish_release_notification,
):
    """Lambda should handle empty event without errors."""
    mock_dynamodb_resource.return_value = MagicMock()
    with patch.dict(
        "os.environ",
        {
            "dynamodb_table_name": "table",
            "release_notification_topic_arn": "arn:aws:sns:us-east-2:123456789012:release-updates",
        },
    ):
        result = aws.lambda_handler({"Records": []}, {})
    mock_publish_release_notification.assert_not_called()
    assert result == {"batchItemFailures": []}


@patch("lambdas.apple_send_update.publish_release_notification")
@patch("lambdas.apple_send_update.mark_release_notified", return_value=False)
@patch("lambdas.apple_send_update.create_dynamodb_resource")
def test_lambda_handler_skips_duplicate_event(
    mock_dynamodb_resource,
    mock_mark_release_notified,
    mock_publish_release_notification,
    dynamodb_event,
):
    mock_dynamodb_resource.return_value = MagicMock()

    with patch.dict(
        "os.environ",
        {
            "dynamodb_table_name": "table",
            "release_notification_topic_arn": "arn:aws:sns:us-east-2:123456789012:release-updates",
        },
    ):
        result = aws.lambda_handler(dynamodb_event, {})

    mock_publish_release_notification.assert_not_called()
    assert result == {"batchItemFailures": []}


def test_format_notification():
    subject, message = aws.format_notification(
        "visionOS",
        "26.0.1",
        "visionOS 26.0.1 released!",
    )

    assert subject == "Apple release update: visionOS 26.0.1"
    assert "visionOS 26.0.1 released!" in message


@patch("lambdas.apple_send_update.notify_error")
def test_lambda_handler_missing_release_topic_reports_failure(
    mock_notify,
    dynamodb_event,
):
    with patch.dict("os.environ", {"dynamodb_table_name": "table"}, clear=True):
        with patch(
            "lambdas.apple_send_update.create_dynamodb_resource"
        ) as mock_dynamodb_resource:
            mock_dynamodb = MagicMock()
            mock_dynamodb.Table.return_value = MagicMock()
            mock_dynamodb_resource.return_value = mock_dynamodb
            with patch(
                "lambdas.apple_send_update.mark_release_notified", return_value=True
            ):
                result = aws.lambda_handler(dynamodb_event, {})

    assert len(result["batchItemFailures"]) == 2
    assert mock_notify.call_count == 2
