resource "aws_sns_topic" "lambda_error_alerts" {
  count = var.error_alert_email != null && trimspace(var.error_alert_email) != "" ? 1 : 0

  name = "apple-update-notification-lambda-errors-${var.environment}"
}

resource "aws_sns_topic" "release_notifications" {
  count = var.release_notification_email != null && trimspace(var.release_notification_email) != "" ? 1 : 0

  name = "apple-update-notification-releases-${var.environment}"
}

resource "aws_sns_topic_subscription" "lambda_error_alert_email" {
  count = var.error_alert_email != null && trimspace(var.error_alert_email) != "" ? 1 : 0

  topic_arn = aws_sns_topic.lambda_error_alerts[0].arn
  protocol  = "email"
  endpoint  = trimspace(var.error_alert_email)
}

resource "aws_sns_topic_subscription" "release_notification_email" {
  count = var.release_notification_email != null && trimspace(var.release_notification_email) != "" ? 1 : 0

  topic_arn = aws_sns_topic.release_notifications[0].arn
  protocol  = "email"
  endpoint  = trimspace(var.release_notification_email)
}
