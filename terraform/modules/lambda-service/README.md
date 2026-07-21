# Module: lambda-service

Creates Lambda application resources, IAM permissions, and artifact uploads.

## Inputs

- `environment`
- `account_id`
- `region`
- `python_version`
- `artifact_bucket_id`
- `dynamodb_table_name`
- `dynamodb_table_arn`
- `dynamodb_table_stream_arn`

## Behavior

- Function names are environment-prefixed with `apple-<environment>-<logical_name>`.
- Lambda artifacts are uploaded from local zip files (`apple_web_scrape.zip`, `apple_send_update.zip`) to S3.
- `apple_web_scrape` receives scheduled execution.
- `apple_send_update` receives DynamoDB stream events and publishes release notifications to SNS.
- IAM policies include:
  - CloudWatch Logs permissions
  - DynamoDB table/stream access scoped per function
  - SNS publish access for error notifications where configured
  - SNS publish access for release notifications on `apple_send_update` only

Schedule map in module locals:

- `development` -> no schedule
- `production` -> `rate(1 hour)`

## Outputs

- `lambda_function_arns`
- `lambda_function_names`
- `lambda_schedules`
- `lambda_functions` (object map containing function name, arn, and optional schedule)