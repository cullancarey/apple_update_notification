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
- `apple_send_update` receives DynamoDB stream events.
- IAM policies include:
  - CloudWatch Logs permissions
  - DynamoDB table/stream access scoped per function
  - SSM read access for tweet credentials only where required

Schedule map in module locals:

- `development` -> `rate(15 minutes)`
- `production` -> `rate(1 hour)`

## Outputs

- `lambda_function_arns`
- `lambda_function_names`
- `lambda_schedules`