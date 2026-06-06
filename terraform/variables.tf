variable "environment" {
  type        = string
  description = "The environment of the Apple update notification project."

  validation {
    condition     = contains(["development", "production"], var.environment)
    error_message = "Environment must be one of: development, production."
  }
}

variable "twitter_username" {
  type        = string
  description = "The username of the twitter account to use."
}

variable "aws_region" {
  type        = string
  description = "AWS region where infrastructure is deployed."
  default     = "us-east-2"
}

variable "error_alert_email" {
  type        = string
  description = "Optional email address for SNS notifications when Lambda errors occur."
  default     = null
}
