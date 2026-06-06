data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  expected_account_ids = {
    development = "693590665244"
    production  = "651295191577"
  }

  account_id     = data.aws_caller_identity.current.account_id
  region         = data.aws_region.current.region
  python_version = "python3.13"
  default_tags = {
    Project     = "apple_update_notification"
    Environment = var.environment
    GitHubRepo  = "github.com/cullancarey/apple_update_notification"
    Terraform   = "true"
  }
}
