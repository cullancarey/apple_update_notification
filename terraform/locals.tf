data "aws_caller_identity" "current" {}

locals {
  lambda_name = "apple_update_notification"
  account_id  = data.aws_caller_identity.current.account_id
}



# primary_s3_origin = var.root_domain_name
# backup_s3_origin  = "backup_${var.root_domain_name}"
