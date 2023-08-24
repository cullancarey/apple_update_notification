resource "aws_dynamodb_table" "apple_os_updates_table" {
  name                        = "apple_os_updates_${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "device"
  deletion_protection_enabled = false
  stream_enabled              = false
  stream_view_type            = "NEW_IMAGE"

  attribute {
    name = "device"
    type = "S"
  }
}
