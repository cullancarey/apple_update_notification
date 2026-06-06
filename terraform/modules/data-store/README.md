# Module: data-store

Creates the DynamoDB table used to track latest Apple OS releases.

## Input

- `environment` (`string`) - Environment suffix for table naming.

## Resources

- `aws_dynamodb_table.apple_os_updates_table`
  - Name format: `apple_os_updates_<environment>`
  - Billing mode: `PAY_PER_REQUEST`
  - Hash key: `device`
  - Stream: enabled (`NEW_IMAGE`)
  - Deletion protection: enabled only in production

## Outputs

- `table_name`
- `table_arn`
- `table_stream_arn`