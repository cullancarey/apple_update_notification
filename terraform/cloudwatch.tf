###########################################################
###### APPLE UPDATE NOTIFICATION LAMBDA CW TRIGGER ########
###########################################################

resource "aws_cloudwatch_event_rule" "apple_update_notification_lambda_rule" {
  name                = "${local.lambda_name}_trigger"
  schedule_expression = "rate(1 hour)"
  description         = "Cloudwatch event rule to trigger the lambda function ${aws_lambda_function.apple_update_notification_lambda.function_name}"
}

resource "aws_cloudwatch_event_target" "apple_update_notification_lambda" {
  rule      = aws_cloudwatch_event_rule.apple_update_notification_lambda_rule.name
  target_id = "trigger_${local.lambda_name}_lambda"
  arn       = aws_lambda_function.apple_update_notification_lambda.arn
}

resource "aws_lambda_permission" "apple_update_notification_lambda_allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.apple_update_notification_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.apple_update_notification_lambda_rule.arn
}