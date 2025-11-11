data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  account_id     = data.aws_caller_identity.current.account_id
  region         = data.aws_region.current.region
  python_version = "python3.13"
}



# primary_s3_origin = var.root_domain_name
# backup_s3_origin  = "backup_${var.root_domain_name}"
