provider "aws" {
  region = "us-east-2"
  default_tags {
    tags = {
      Project     = "apple_update_notification"
      Environment = var.environment
    }
  }
}

terraform {
  backend "s3" {
  }
}


provider "aws" {
  alias  = "cloudfront-certificate"
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "apple_update_notification"
      Environment = var.environment
    }
  }
}

provider "aws" {
  alias  = "backup_sign_up_bucket_region"
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "apple_update_notification"
      Environment = var.environment
    }
  }
}
