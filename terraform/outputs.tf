output "dynamodb_table_name" {
  description = "DynamoDB table name for Apple OS updates"
  value       = module.data_store.table_name
}

output "lambda_function_arns" {
  description = "Lambda function ARNs keyed by logical function name"
  value       = module.lambda_service.lambda_function_arns
}

output "artifact_bucket_name" {
  description = "S3 bucket used for Lambda deployment artifacts"
  value       = module.storage.bucket_id
}
