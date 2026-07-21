from unittest.mock import patch

from lambdas.apple_utils import (
    notify_error,
    publish_release_notification,
)


@patch("lambdas.apple_utils.sns_client.publish")
def test_notify_error_publishes_when_topic_configured(mock_publish):
    with patch.dict(
        "os.environ",
        {"error_alert_topic_arn": "arn:aws:sns:us-east-2:123456789012:alerts"},
    ):
        notify_error(
            source="apple_web_scrape",
            error_message="test error",
            details={"event_id": "evt-1"},
        )

    mock_publish.assert_called_once()
    publish_kwargs = mock_publish.call_args.kwargs
    assert publish_kwargs["TopicArn"] == "arn:aws:sns:us-east-2:123456789012:alerts"
    assert "apple_web_scrape" in publish_kwargs["Subject"]
    assert "test error" in publish_kwargs["Message"]


@patch("lambdas.apple_utils.sns_client.publish")
def test_notify_error_noop_without_topic(mock_publish):
    with patch.dict("os.environ", {}, clear=True):
        notify_error(source="apple_web_scrape", error_message="test error")

    mock_publish.assert_not_called()


@patch("lambdas.apple_utils.sns_client.publish")
def test_publish_release_notification_publishes_when_topic_configured(mock_publish):
    with patch.dict(
        "os.environ",
        {
            "release_notification_topic_arn": "arn:aws:sns:us-east-2:123456789012:release-updates"
        },
    ):
        publish_release_notification(
            subject="Apple release update: iOS 26.0.1",
            message="A new Apple release was detected.",
        )

    mock_publish.assert_called_once_with(
        TopicArn="arn:aws:sns:us-east-2:123456789012:release-updates",
        Subject="Apple release update: iOS 26.0.1",
        Message="A new Apple release was detected.",
    )


@patch("lambdas.apple_utils.sns_client.publish")
def test_publish_release_notification_noop_without_topic(mock_publish):
    with patch.dict("os.environ", {}, clear=True):
        publish_release_notification(
            subject="Apple release update: iOS 26.0.1",
            message="A new Apple release was detected.",
        )

    mock_publish.assert_not_called()
