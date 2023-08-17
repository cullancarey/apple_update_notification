variable "root_domain_name" {
  type        = string
  default     = "appleupdatenotification.com"
  description = "The domain name of my Apple update notification project sign up page."
}

# variable "subscription_intake_api_domain" {
#   type        = string
#   description = "The domain name of the api gateway resource that intakes the subscription information."
# }

variable "environment" {
  type        = string
  description = "The environment of the Apple update notification project."
}

variable "twitter_username" {
  type        = string
  description = "The username of the twitter account to use."
}
