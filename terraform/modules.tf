module "data_store" {
  source = "./modules/data-store"

  environment = var.environment
}

module "storage" {
  source = "./modules/storage"

  account_id = local.account_id
}

module "lambda_service" {
  source = "./modules/lambda-service"

  environment                    = var.environment
  account_id                     = local.account_id
  region                         = local.region
  python_version                 = local.python_version
  artifact_bucket_id             = module.storage.bucket_id
  dynamodb_table_name            = module.data_store.table_name
  dynamodb_table_arn             = module.data_store.table_arn
  dynamodb_table_stream_arn      = module.data_store.table_stream_arn
  error_alert_topic_arn          = try(aws_sns_topic.lambda_error_alerts[0].arn, null)
  release_notification_topic_arn = try(aws_sns_topic.release_notifications[0].arn, null)
}

module "observability" {
  source = "./modules/observability"

  environment           = var.environment
  lambda_functions      = module.lambda_service.lambda_functions
  error_alert_topic_arn = try(aws_sns_topic.lambda_error_alerts[0].arn, null)
}
