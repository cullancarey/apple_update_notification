# Module: storage

Creates the S3 artifact bucket used for Lambda deployment packages.

## Input

- `account_id` (`string`) - Account identifier used in bucket naming.

## Resources

- `aws_s3_bucket.apple_update_notification_bucket`
- `aws_s3_bucket_public_access_block.apple_update_notification_bucket_access_block`
- `aws_s3_bucket_versioning.apple_update_notification_bucket_versioning` (enabled)
- `aws_s3_bucket_server_side_encryption_configuration.apple_update_notification_bucket_sse` (AES256)
- `aws_s3_bucket_lifecycle_configuration.apple_update_notification_bucket_lifecycle_config`
  - Current object expiration: 60 days
  - Noncurrent object version expiration: 60 days
- `aws_s3_bucket_policy.apple_update_notification_bucket_policy`
  - Denies non-TLS (`aws:SecureTransport = false`) access

## Outputs

- `bucket_id`
- `bucket_arn`