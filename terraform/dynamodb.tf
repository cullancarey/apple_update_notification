resource "aws_dynamodb_table" "apple_os_updates_table" {
  name                        = "apple_os_updates_${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "timestamp"
  deletion_protection_enabled = true
  stream_enabled              = true
  stream_view_type            = "NEW_IMAGE"

  attribute {
    name = "timestamp"
    type = "N"
  }
}
