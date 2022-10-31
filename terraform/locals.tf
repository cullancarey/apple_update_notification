data "aws_caller_identity" "current" {}

locals {
  lambda_name          = "apple_update_notification"
  s3_bucket_for_lambda = "apple_update_notification_bucket"
  account_id           = data.aws_caller_identity.current.account_id
}