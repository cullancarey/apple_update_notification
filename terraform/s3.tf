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
