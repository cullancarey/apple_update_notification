variable "account_id" {
  type = string
}

resource "aws_s3_bucket" "apple_update_notification_bucket" {
  #checkov:skip=CKV_AWS_144:Cross-region replication is not required for this artifact bucket.
  bucket = "apple-update-notification-${var.account_id}"
  tags = {
    Name = "apple-update-notification-${var.account_id}"
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

resource "aws_s3_bucket_server_side_encryption_configuration" "apple_update_notification_bucket_sse" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "apple_update_notification_bucket_lifecycle_config" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id

  rule {
    id = "ExpireAllAfter2Month"

    expiration {
      days = 60
    }

    noncurrent_version_expiration {
      noncurrent_days = 60
    }

    status = "Enabled"
  }
}

data "aws_iam_policy_document" "deny_insecure_transport" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.apple_update_notification_bucket.arn,
      "${aws_s3_bucket.apple_update_notification_bucket.arn}/*"
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "apple_update_notification_bucket_policy" {
  bucket = aws_s3_bucket.apple_update_notification_bucket.id
  policy = data.aws_iam_policy_document.deny_insecure_transport.json
}

output "bucket_id" {
  value = aws_s3_bucket.apple_update_notification_bucket.id
}

output "bucket_arn" {
  value = aws_s3_bucket.apple_update_notification_bucket.arn
}
