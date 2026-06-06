# Module: observability

Creates CloudWatch and EventBridge resources for Lambda logging and scheduled execution.

## Inputs

- `environment`
- `lambda_function_names` (map)
- `lambda_function_arns` (map)
- `lambda_schedules` (map)

## Resources

- `aws_cloudwatch_log_group.lambda_logs`
  - One log group per Lambda name
  - Retention: 365 days for production, 180 days otherwise
- `aws_cloudwatch_event_rule.lambda_schedules`
  - One schedule rule per scheduled Lambda
- `aws_cloudwatch_event_target.lambda_targets`
  - Binds schedule rule to Lambda ARN
- `aws_lambda_permission.allow_cloudwatch_invoke`
  - Allows EventBridge to invoke scheduled Lambdas

This module intentionally focuses on baseline logs and schedules; alerts/metrics can be layered on separately.