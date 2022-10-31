######################################################
######### APPLE UPDATE NOTIFICATION BUCKET ###########
######################################################


resource "aws_s3_bucket" "apple_update_notification_bucket" {
  bucket = "apple-update-notification"
  tags = {
    "Name" = "${local.s3_bucket_for_lambda}"
  }
}


resource "aws_s3_bucket_policy" "allow_access_from_lambda_user" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id
  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowLambda",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${local.account_id}:role/service-role/${aws_iam_role.iam_for_apple_update_notification_lambda.name}"
            },
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": ["arn:aws:s3:::${local.s3_bucket_for_lambda}/*", "arn:aws:s3:::${local.s3_bucket_for_lambda}"]
        }
    ]
}
POLICY
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