data "aws_caller_identity" "current" {}

locals {
  lambda_name = "apple_update_notification"
  account_id  = data.aws_caller_identity.current.account_id
}