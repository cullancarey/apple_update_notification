resource "aws_lambda_layer_version" "lambda_utils_layer" {
  filename   = "apple_utils.zip"
  layer_name = "apple_utils"

  compatible_runtimes = ["python3.9"]
}
