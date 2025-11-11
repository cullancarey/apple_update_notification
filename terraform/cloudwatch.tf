###########################################################
###### CLOUDWATCH EVENT (SCHEDULED TRIGGERS FOR LAMBDAS) ##
###########################################################

# Extend the lambda_definitions in lambda_common.tf
# Add this key for any lambda you want to schedule.
# Example (inside locals in lambda_common.tf):
# apple_web_scrape = {
#   description      = "Scrapes Apple site and updates DynamoDB"
#   dynamodb_actions = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
#   extra_ssm_access = false
#   stream_access    = false
#   schedule         = "rate(1 hour)"  # 👈 add this line
# }

locals {
  scheduled_lambdas = {
    for name, cfg in local.lambda_definitions : name => cfg
    if lookup(cfg, "schedule", null) != null
  }
}

# 1️⃣ CloudWatch rule (only for lambdas with a schedule)
resource "aws_cloudwatch_event_rule" "lambda_schedules" {
  for_each            = local.scheduled_lambdas
  description         = "Scheduled rule to trigger ${each.key} lambda"
  schedule_expression = each.value.schedule
}

# 2️⃣ Event target linking CloudWatch rule → Lambda
resource "aws_cloudwatch_event_target" "lambda_targets" {
  for_each  = local.scheduled_lambdas
  rule      = aws_cloudwatch_event_rule.lambda_schedules[each.key].name
  target_id = "trigger_${each.key}_lambda"
  arn       = aws_lambda_function.lambda_functions[each.key].arn
}

# 3️⃣ Lambda permission so CloudWatch Events can invoke it
resource "aws_lambda_permission" "allow_cloudwatch_invoke" {
  for_each      = local.scheduled_lambdas
  statement_id  = "AllowExecutionFromCloudWatch_${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_functions[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedules[each.key].arn
}
