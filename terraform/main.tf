provider "aws" {
  region = "us-east-2"
  default_tags {
    tags = {
      Project = "apple_update_notification"
    }
  }
}

terraform {
  backend "s3" {
  }
}