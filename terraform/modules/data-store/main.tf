variable "environment" {
  type = string
}

resource "aws_dynamodb_table" "apple_os_updates_table" {
  name                        = "apple_os_updates_${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "device"
  deletion_protection_enabled = var.environment == "production"
  stream_enabled              = true
  stream_view_type            = "NEW_IMAGE"

  attribute {
    name = "device"
    type = "S"
  }
}

output "table_name" {
  value = aws_dynamodb_table.apple_os_updates_table.name
}

output "table_arn" {
  value = aws_dynamodb_table.apple_os_updates_table.arn
}

output "table_stream_arn" {
  value = aws_dynamodb_table.apple_os_updates_table.stream_arn
}
