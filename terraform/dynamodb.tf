resource "aws_dynamodb_table" "apple_os_updates_table" {
  name         = "apple_os_updates_${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "RowId"

  attribute {
    name = "RowId"
    type = "S"
  }
}
