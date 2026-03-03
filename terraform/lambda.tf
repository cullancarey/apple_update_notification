#############################################
############## SHARED LOCALS ################
#############################################

locals {
  # region/account_id defined elsewhere
  common_log_actions = [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ]

  common_s3_actions = [
    "s3:GetObject",
    "s3:ListBucket"
  ]

  lambda_definitions = {
    apple_web_scrape = {
      description      = "Scrapes Apple site and updates DynamoDB"
      dynamodb_actions = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      extra_ssm_access = false
      stream_access    = false
      schedule         = var.environment == "develop" ? "rate(15 minutes)" : "rate(1 hour)"
    }

    apple_send_update = {
      description = "Triggered by DynamoDB stream to tweet updates"
      dynamodb_actions = [
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:DescribeStream",
        "dynamodb:ListStreams"
      ]
      extra_ssm_access = true
      stream_access    = true
    }
  }
}

#############################################
############### TRUST POLICY ################
#############################################

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

#############################################
########## DYNAMIC IAM ROLE SETUP ###########
#############################################

resource "aws_iam_role" "lambda_roles" {
  for_each           = local.lambda_definitions
  path               = "/service-role/"
  description        = "IAM role for ${each.key} Lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_policies" {
  for_each = local.lambda_definitions

  # CloudWatch Logging
  statement {
    sid       = "CloudWatchLogging"
    actions   = local.common_log_actions
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:*"]
    effect    = "Allow"
  }

  # S3 Bucket Access
  statement {
    sid     = "S3Access"
    actions = local.common_s3_actions
    resources = [
      aws_s3_bucket.apple_update_notification_bucket.arn,
      "${aws_s3_bucket.apple_update_notification_bucket.arn}/*"
    ]
    effect = "Allow"
  }

  # DynamoDB Access
  statement {
    sid     = "DynamoDBAccess"
    actions = each.value.dynamodb_actions
    resources = concat(
      [aws_dynamodb_table.apple_os_updates_table.arn],
      each.value.stream_access ? [aws_dynamodb_table.apple_os_updates_table.stream_arn] : []
    )
    effect = "Allow"
  }

  # SSM Access (conditionally for send_update)
  dynamic "statement" {
    for_each = each.value.extra_ssm_access ? [1] : []
    content {
      sid     = "ParameterStoreAccess"
      actions = ["ssm:GetParameters"]
      resources = [
        "arn:aws:ssm:${local.region}:${local.account_id}:parameter/apple_update_notification_*"
      ]
      effect = "Allow"
    }
  }
}

resource "aws_iam_role_policy" "lambda_policies" {
  for_each = local.lambda_definitions
  role     = aws_iam_role.lambda_roles[each.key].id
  policy   = data.aws_iam_policy_document.lambda_policies[each.key].json
}


#############################################
########## PACKAGE + DEPLOY LAMBDAS #########
#############################################

# NOTE: Lambda packages are built by GitHub Actions (create_lambda_package.sh)
# and downloaded as artifacts into the terraform/ directory before this runs.
# Each package contains: handler.py + apple_utils.py + dependencies

# Upload each pre-built zip to S3
resource "aws_s3_object" "lambda_objects" {
  for_each    = local.lambda_definitions
  bucket      = aws_s3_bucket.apple_update_notification_bucket.id
  key         = "${each.key}.zip"
  source      = "${each.key}.zip"
  source_hash = filemd5("${each.key}.zip")
}

# Deploy each Lambda
resource "aws_lambda_function" "lambda_functions" {
  for_each         = local.lambda_definitions
  s3_bucket        = aws_s3_bucket.apple_update_notification_bucket.id
  s3_key           = aws_s3_object.lambda_objects[each.key].key
  function_name    = each.key
  description      = each.value.description
  role             = aws_iam_role.lambda_roles[each.key].arn
  handler          = "${each.key}.lambda_handler"
  runtime          = local.python_version
  timeout          = 90
  source_code_hash = filemd5("${each.key}.zip")

  environment {
    variables = merge(
      {
        environment = var.environment
      },
      each.key == "apple_web_scrape" ? {
        dynamodb_table_name = aws_dynamodb_table.apple_os_updates_table.name
      } : {}
    )
  }
}

# Add DynamoDB stream trigger only for lambdas that require it
resource "aws_lambda_event_source_mapping" "lambda_event_mappings" {
  for_each = {
    for name, cfg in local.lambda_definitions : name => cfg
    if cfg.stream_access
  }

  event_source_arn  = aws_dynamodb_table.apple_os_updates_table.stream_arn
  function_name     = aws_lambda_function.lambda_functions[each.key].arn
  starting_position = "LATEST"
}
