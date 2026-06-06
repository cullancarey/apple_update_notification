variable "environment" {
  type = string
}

variable "lambda_functions" {
  type = map(object({
    name     = string
    arn      = string
    schedule = optional(string)
  }))
}

locals {
  scheduled_lambdas = {
    for key, fn in var.lambda_functions : key => fn
    if try(fn.schedule, null) != null
  }
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = var.lambda_functions

  name              = "/aws/lambda/${each.value.name}"
  retention_in_days = var.environment == "production" ? 365 : 180
}

resource "aws_cloudwatch_event_rule" "lambda_schedules" {
  for_each = local.scheduled_lambdas

  description         = "Scheduled rule to trigger ${each.key} lambda"
  schedule_expression = each.value.schedule
}

resource "aws_cloudwatch_event_target" "lambda_targets" {
  for_each = local.scheduled_lambdas

  rule      = aws_cloudwatch_event_rule.lambda_schedules[each.key].name
  target_id = "trigger_${each.key}_lambda"
  arn       = each.value.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_invoke" {
  for_each = local.scheduled_lambdas

  statement_id  = "AllowExecutionFromCloudWatch_${each.key}_${var.environment}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedules[each.key].arn
}
