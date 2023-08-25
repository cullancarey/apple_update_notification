######################################################
######### APPLE UPDATE NOTIFICATION BUCKET ###########
######################################################


resource "aws_s3_bucket" "apple_update_notification_bucket" {
  #checkov:skip=CKV_AWS_144:Ensure that S3 bucket has cross-region replication enabled
  bucket = "apple-update-notification-${local.account_id}"
  tags = {
    "Name" = "apple-update-notification-${local.account_id}"
  }
}

data "aws_iam_policy_document" "allow_access_from_lambda_user_policy_document" {
  statement {
    sid    = "AllowLambda"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.iam_for_apple_web_scrape_lambda.arn]
    }

    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]

    resources = [
      "${aws_s3_bucket.apple_update_notification_bucket.arn}/*",
      aws_s3_bucket.apple_update_notification_bucket.arn
    ]
  }
}


resource "aws_s3_bucket_policy" "allow_access_from_lambda_user" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id
  policy = data.aws_iam_policy_document.allow_access_from_lambda_user_policy_document.json
}



resource "aws_s3_bucket_public_access_block" "apple_update_notification_bucket_access_block" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket_versioning" "apple_update_notification_bucket_versioning" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}


resource "aws_s3_bucket_lifecycle_configuration" "apple_update_notification_bucket_lifecycle_config" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id

  rule {
    id = "ExpireAllAfter2Month"

    expiration {
      days = 60
    }

    status = "Enabled"
  }
}


######################################################
########### PRIMARY SIGN-UP BUCKET ###################
######################################################

# resource "aws_s3_bucket" "sign_up_bucket" {
#   bucket = var.root_domain_name

#   tags = {
#     Name = "sign_up_bucket"
#   }
# }

# resource "aws_s3_bucket_public_access_block" "s3Public" {
#   bucket                  = aws_s3_bucket.sign_up_bucket.id
#   block_public_acls       = true
#   block_public_policy     = true
#   restrict_public_buckets = true
#   ignore_public_acls      = true
# }


# resource "aws_s3_bucket_website_configuration" "sign_up_bucket_config" {
#   bucket = aws_s3_bucket.sign_up_bucket.bucket

#   index_document {
#     suffix = "index.html"
#   }

#   error_document {
#     key = "error.html"
#   }
# }

# resource "aws_s3_bucket_versioning" "sign_up_bucket_versioning" {
#   bucket = aws_s3_bucket.sign_up_bucket.id
#   versioning_configuration {
#     status = "Enabled"
#   }
# }

# resource "aws_s3_bucket_replication_configuration" "sign_up_bucket_replication" {
#   # Must have bucket versioning enabled first
#   depends_on = [aws_s3_bucket_versioning.sign_up_bucket_versioning]

#   role   = aws_iam_role.replication.arn
#   bucket = aws_s3_bucket.sign_up_bucket.id

#   rule {
#     id     = "backup_sign_up_bucket"
#     status = "Enabled"
#     destination {
#       bucket = aws_s3_bucket.backup_sign_up_bucket.arn
#     }
#   }
# }

# resource "aws_s3_bucket_lifecycle_configuration" "sign_up_bucket_lifecycle_rule" {
#   bucket = aws_s3_bucket.sign_up_bucket.id

#   rule {
#     id     = "delete versions"
#     status = "Enabled"
#     noncurrent_version_expiration {
#       noncurrent_days = 2
#     }
#   }
# }

# resource "aws_s3_bucket_policy" "sign_up_bucket_policy" {
#   bucket = aws_s3_bucket.sign_up_bucket.id
#   policy = <<POLICY
# {
#     "Version": "2012-10-17",
#     "Statement": {
#         "Sid": "AllowCloudFrontServicePrincipalReadOnly",
#         "Effect": "Allow",
#         "Principal": {
#             "Service": "cloudfront.amazonaws.com"
#         },
#         "Action": "s3:GetObject",
#         "Resource": "${aws_s3_bucket.sign_up_bucket.arn}/*",
#         "Condition": {
#             "StringEquals": {
#                 "AWS:SourceArn": "${aws_cloudfront_distribution.sign_up_bucket_distribution.arn}"
#             }
#         }
#     }
# }

# POLICY
# }


# ######################################################
# ############ BACKUP SIGN-UP BUCKET ###################
# ######################################################


# resource "aws_s3_bucket" "backup_sign_up_bucket" {
#   bucket   = "backup-${var.root_domain_name}"
#   provider = aws.backup_sign_up_bucket_region
#   tags = {
#     Name = "backup_sign_up_bucket"
#   }
# }

# resource "aws_s3_bucket_public_access_block" "backup_sign_up_bucket_s3Public" {
#   bucket                  = aws_s3_bucket.backup_sign_up_bucket.id
#   provider                = aws.backup_sign_up_bucket_region
#   block_public_acls       = true
#   block_public_policy     = true
#   restrict_public_buckets = true
#   ignore_public_acls      = true
# }


# resource "aws_s3_bucket_website_configuration" "backup_sign_up_bucket_config" {
#   bucket   = aws_s3_bucket.backup_sign_up_bucket.bucket
#   provider = aws.backup_sign_up_bucket_region

#   index_document {
#     suffix = "index.html"
#   }

#   error_document {
#     key = "error.html"
#   }
# }

# resource "aws_s3_bucket_versioning" "backup_sign_up_bucket_versioning" {
#   bucket   = aws_s3_bucket.backup_sign_up_bucket.id
#   provider = aws.backup_sign_up_bucket_region
#   versioning_configuration {
#     status = "Enabled"
#   }
# }

# resource "aws_s3_bucket_lifecycle_configuration" "backup_sign_up_bucket_lifecycle_rule" {
#   bucket   = aws_s3_bucket.backup_sign_up_bucket.id
#   provider = aws.backup_sign_up_bucket_region

#   rule {
#     id     = "delete versions"
#     status = "Enabled"
#     noncurrent_version_expiration {
#       noncurrent_days = 2
#     }
#   }
# }

# resource "aws_s3_bucket_policy" "backup_sign_up_bucket_policy" {
#   bucket   = aws_s3_bucket.backup_sign_up_bucket.id
#   provider = aws.backup_sign_up_bucket_region
#   policy   = <<POLICY
# {
#     "Version": "2012-10-17",
#     "Statement": {
#         "Sid": "AllowCloudFrontServicePrincipalReadOnly",
#         "Effect": "Allow",
#         "Principal": {
#             "Service": "cloudfront.amazonaws.com"
#         },
#         "Action": "s3:GetObject",
#         "Resource": "${aws_s3_bucket.backup_sign_up_bucket.arn}/*",
#         "Condition": {
#             "StringEquals": {
#                 "AWS:SourceArn": "${aws_cloudfront_distribution.sign_up_bucket_distribution.arn}"
#             }
#         }
#     }
# }

# POLICY
# }


# resource "aws_iam_role" "replication" {
#   name = "s3crr_role_for_${var.root_domain_name}"
#   path = "/service-role/"

#   assume_role_policy = <<POLICY
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Principal": {
#         "Service": "s3.amazonaws.com"
#       },
#       "Action": "sts:AssumeRole"
#     }
#   ]
# }

# POLICY
# }


# resource "aws_iam_policy" "s3_replication_exec_policy" {
#   name   = "s3crr_policy_for_${var.root_domain_name}"
#   path   = "/service-role/"
#   policy = <<POLICY
# {
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Action": [
#                 "s3:ListBucket",
#                 "s3:GetReplicationConfiguration",
#                 "s3:GetObjectVersionForReplication",
#                 "s3:GetObjectVersionAcl",
#                 "s3:GetObjectVersionTagging",
#                 "s3:GetObjectRetention",
#                 "s3:GetObjectLegalHold"
#             ],
#             "Effect": "Allow",
#             "Resource": [
#                 "${aws_s3_bucket.sign_up_bucket.arn}",
#                 "${aws_s3_bucket.sign_up_bucket.arn}/*",
#                 "${aws_s3_bucket.backup_sign_up_bucket.arn}",
#                 "${aws_s3_bucket.backup_sign_up_bucket.arn}/*"
#             ]
#         },
#         {
#             "Action": [
#                 "s3:ReplicateObject",
#                 "s3:ReplicateDelete",
#                 "s3:ReplicateTags",
#                 "s3:ObjectOwnerOverrideToBucketOwner"
#             ],
#             "Effect": "Allow",
#             "Resource": [
#                 "${aws_s3_bucket.sign_up_bucket.arn}/*",
#                 "${aws_s3_bucket.backup_sign_up_bucket.arn}/*"
#             ]
#         }
#     ]
# }

# POLICY
# }

# resource "aws_iam_role_policy_attachment" "s3_attach" {
#   role       = aws_iam_role.replication.name
#   policy_arn = aws_iam_policy.s3_replication_exec_policy.arn
# }
