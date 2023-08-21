#############################################
########## APPLE WEB SCRAPE LAMBDA #########
#############################################

locals {
  web_scrape_lambda_name = "apple_web_scrape"
}

data "archive_file" "apple_web_scrape_lambda" {
  type        = "zip"
  source_file = "../lambdas/${local.web_scrape_lambda_name}.py"
  output_path = "${local.web_scrape_lambda_name}.zip"
}

resource "aws_s3_object" "apple_web_scrape_lambda_file" {
  bucket      = aws_s3_bucket.apple_update_notification_bucket.id
  key         = "${local.web_scrape_lambda_name}.zip"
  source      = "${local.web_scrape_lambda_name}.zip"
  source_hash = data.archive_file.apple_web_scrape_lambda.output_base64sha512
}

resource "aws_lambda_function" "apple_web_scrape_lambda" {
  s3_bucket     = aws_s3_bucket.apple_update_notification_bucket.id
  s3_key        = aws_s3_object.apple_web_scrape_lambda_file.id
  function_name = local.web_scrape_lambda_name
  role          = aws_iam_role.iam_for_apple_web_scrape_lambda.arn
  handler       = "${local.web_scrape_lambda_name}.lambda_handler"
  description   = "Lambda function for sending notifications about the newest apple releases"

  source_code_hash = data.archive_file.apple_web_scrape_lambda.output_base64sha512

  layers = [aws_lambda_layer_version.lambda_utils_layer.arn]

  environment {
    variables = {
      website             = var.root_domain_name
      environment         = var.environment
      twitter_username    = var.twitter_username
      dynamodb_table_name = aws_dynamodb_table.apple_os_updates_table.id
    }
  }

  runtime = "python3.9"
  timeout = 90
}

data "aws_iam_policy_document" "iam_for_apple_web_scrape_lambda_policy_document" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "iam_for_apple_web_scrape_lambda" {
  name        = "${local.web_scrape_lambda_name}_role"
  path        = "/service-role/"
  description = "IAM role for ${local.web_scrape_lambda_name} lambda."

  assume_role_policy = aws_iam_policy_document.iam_for_apple_web_scrape_lambda_policy_document.json
}

data "aws_iam_policy_document" "apple_web_scrape_lambda_iam_policy_document" {
  statement {
    sid = "AllowCloudwatch"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup",
    ]
    resources = [
      "arn:aws:logs:us-east-2:${local.account_id}:log-group:/aws/lambda/${local.web_scrape_lambda_name}:*",
      "arn:aws:logs:us-east-2:${local.account_id}:*",
    ]
    effect = "Allow"
  }

  statement {
    sid = "AllowDynamoDB"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
    ]
    resources = [aws_dynamodb_table.apple_os_updates_table.arn]
    effect    = "Allow"
  }

  statement {
    sid = "AllowS3"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = ["${aws_s3_bucket.apple_update_notification_bucket.arn}/*"]
    effect    = "Allow"
  }

  statement {
    sid = "AllowParameterStore"
    actions = [
      "ssm:GetParameter",
    ]
    resources = [
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_api_key_${var.environment}",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_secret_key_${var.environment}",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_twitter_access_token_${var.environment}",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_access_secret_token_${var.environment}"
    ]
    effect = "Allow"
  }
}


resource "aws_iam_policy" "apple_web_scrape_lambda_iam_policy" {
  name        = "${local.web_scrape_lambda_name}_role_policy"
  path        = "/service-role/"
  description = "IAM policy for ${aws_iam_role.iam_for_apple_web_scrape_lambda.name}"
  policy      = aws_iam_policy_document.apple_web_scrape_lambda_iam_policy_document.json
}

resource "aws_iam_role_policy_attachment" "apple_web_scrape_lambda_attach" {
  role       = aws_iam_role.iam_for_apple_web_scrape_lambda.name
  policy_arn = aws_iam_policy.apple_web_scrape_lambda_iam_policy.arn
}
