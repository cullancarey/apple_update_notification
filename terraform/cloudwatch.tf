###########################################################
###### APPLE UPDATE NOTIFICATION LAMBDA CW TRIGGER ########
###########################################################

resource "aws_cloudwatch_event_rule" "apple_web_scrape_lambda_rule" {
  name                = "${local.web_scrape_lambda_name}_trigger"
  schedule_expression = "rate(1 hour)"
  description         = "Cloudwatch event rule to trigger the lambda function ${aws_lambda_function.apple_web_scrape_lambda.function_name}"
}

resource "aws_cloudwatch_event_target" "apple_web_scrape_lambda" {
  rule      = aws_cloudwatch_event_rule.apple_web_scrape_lambda_rule.name
  target_id = "trigger_${local.web_scrape_lambda_name}_lambda"
  arn       = aws_lambda_function.apple_web_scrape_lambda.arn
}

resource "aws_lambda_permission" "apple_web_scrape_lambda_allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.apple_web_scrape_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.apple_web_scrape_lambda_rule.arn
}
