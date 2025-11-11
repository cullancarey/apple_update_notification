#############################################
#### APPLE UPDATE NOTIFICATION LAMBDA #######
#############################################


locals {
  send_update_lambda_name = "apple_send_update"
}

data "archive_file" "apple_send_update_lambda" {
  type        = "zip"
  source_file = "../lambdas/${local.send_update_lambda_name}.py"
  output_path = "${local.send_update_lambda_name}.zip"
}

resource "aws_s3_object" "apple_send_update_lambda_file" {
  bucket      = aws_s3_bucket.apple_update_notification_bucket.id
  key         = "${local.send_update_lambda_name}.zip"
  source      = "${local.send_update_lambda_name}.zip"
  source_hash = data.archive_file.apple_send_update_lambda.output_base64sha512
}

resource "aws_lambda_function" "apple_send_update_lambda" {
  s3_bucket     = aws_s3_bucket.apple_update_notification_bucket.id
  s3_key        = aws_s3_object.apple_send_update_lambda_file.key
  function_name = local.send_update_lambda_name
  role          = aws_iam_role.iam_for_apple_send_update_lambda.arn
  handler       = "${local.send_update_lambda_name}.lambda_handler"
  description   = "Lambda function for sending notifications about the newest apple releases"

  source_code_hash = data.archive_file.apple_send_update_lambda.output_base64sha512

  layers = [aws_lambda_layer_version.lambda_utils_layer.arn]

  runtime = local.python_version
  timeout = 90

}

data "aws_iam_policy_document" "iam_for_apple_send_update_lambda_policy_document" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "iam_for_apple_send_update_lambda" {
  name        = "${local.send_update_lambda_name}_role"
  path        = "/service-role/"
  description = "IAM role for ${local.send_update_lambda_name} lambda."

  assume_role_policy = data.aws_iam_policy_document.iam_for_apple_send_update_lambda_policy_document.json
}

data "aws_iam_policy_document" "apple_send_update_lambda_iam_policy_document" {
  statement {
    sid = "AllowCloudwatch"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup",
    ]
    resources = [
      "arn:aws:logs:us-east-2:${local.account_id}:log-group:/aws/lambda/${local.send_update_lambda_name}:*",
      "arn:aws:logs:us-east-2:${local.account_id}:*",
    ]
    effect = "Allow"
  }

  statement {
    sid = "AllowS3"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.apple_update_notification_bucket.arn,
      "${aws_s3_bucket.apple_update_notification_bucket.arn}/*"
    ]
    effect = "Allow"
  }

  statement {
    sid = "AllowDynamoDB"
    actions = [
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:DescribeStream",
      "dynamodb:ListStreams",
    ]
    resources = [aws_dynamodb_table.apple_os_updates_table.arn, aws_dynamodb_table.apple_os_updates_table.stream_arn]
    effect    = "Allow"
  }

  statement {
    sid = "AllowParameterStore"
    actions = [
      "ssm:GetParameter",
    ]
    resources = [
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_api_key",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_bearer_token",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_secret_key",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_twitter_access_token",
      "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_access_secret_token"
    ]
    effect = "Allow"
  }
}

resource "aws_iam_policy" "apple_send_update_lambda_iam_policy" {
  name        = "${local.send_update_lambda_name}_role_policy"
  path        = "/service-role/"
  description = "IAM policy for ${aws_iam_role.iam_for_apple_send_update_lambda.name}"
  policy      = data.aws_iam_policy_document.apple_send_update_lambda_iam_policy_document.json

}

resource "aws_iam_role_policy_attachment" "apple_send_update_lambda_attach" {
  role       = aws_iam_role.iam_for_apple_send_update_lambda.name
  policy_arn = aws_iam_policy.apple_send_update_lambda_iam_policy.arn
}


resource "aws_lambda_event_source_mapping" "apple_send_update_lambda_event_mapping" {
  event_source_arn  = aws_dynamodb_table.apple_os_updates_table.stream_arn
  function_name     = aws_lambda_function.apple_send_update_lambda.arn
  starting_position = "LATEST"
}
