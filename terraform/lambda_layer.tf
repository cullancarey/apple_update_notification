resource "aws_s3_object" "lambda_layer_deployment_package_file" {
  bucket      = aws_s3_bucket.apple_update_notification_bucket.id
  key         = "apple_utils.zip"
  source      = "apple_utils.zip"
  source_hash = filemd5("apple_utils.zip")
}


resource "aws_lambda_layer_version" "lambda_utils_layer" {
  s3_bucket         = aws_s3_bucket.apple_update_notification_bucket.id
  s3_key            = aws_s3_object.lambda_layer_deployment_package_file.key
  s3_object_version = aws_s3_object.lambda_layer_deployment_package_file.version_id
  layer_name        = "apple_utils"

  compatible_runtimes = ["python3.13"]
}
