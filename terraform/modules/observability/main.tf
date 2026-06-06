variable "environment" {
  type = string
}

variable "lambda_function_names" {
  type = map(string)
}

variable "lambda_function_arns" {
  type = map(string)
}

variable "lambda_schedules" {
  type = map(string)
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = var.lambda_function_names

  name              = "/aws/lambda/${each.value}"
  retention_in_days = var.environment == "production" ? 365 : 180
}

resource "aws_cloudwatch_event_rule" "lambda_schedules" {
  for_each = var.lambda_schedules

  description         = "Scheduled rule to trigger ${each.key} lambda"
  schedule_expression = each.value
}

resource "aws_cloudwatch_event_target" "lambda_targets" {
  for_each = var.lambda_schedules

  rule      = aws_cloudwatch_event_rule.lambda_schedules[each.key].name
  target_id = "trigger_${each.key}_lambda"
  arn       = var.lambda_function_arns[each.key]
}

resource "aws_lambda_permission" "allow_cloudwatch_invoke" {
  for_each = var.lambda_schedules

  statement_id  = "AllowExecutionFromCloudWatch_${each.key}_${var.environment}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_names[each.key]
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedules[each.key].arn
}
