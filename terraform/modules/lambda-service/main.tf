variable "environment" {
  type = string
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "python_version" {
  type = string
}

variable "artifact_bucket_id" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "dynamodb_table_arn" {
  type = string
}

variable "dynamodb_table_stream_arn" {
  type = string
}

variable "error_alert_topic_arn" {
  type    = string
  default = null
}

variable "release_notification_topic_arn" {
  type    = string
  default = null
}

locals {
  name_prefix = "apple-${var.environment}"

  schedule_by_env = {
    development = null
    production  = "rate(1 hour)"
  }

  lambda_definitions = {
    apple_web_scrape = {
      description                 = "Scrapes Apple site and updates DynamoDB"
      dynamodb_actions            = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      release_notification_access = true
      stream_access               = false
      schedule                    = local.schedule_by_env[var.environment]
    }
  }

  scheduled_lambdas = {
    for name, cfg in local.lambda_definitions : name => cfg
    if lookup(cfg, "schedule", null) != null
  }
}

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

resource "aws_iam_role" "lambda_roles" {
  for_each           = local.lambda_definitions
  path               = "/service-role/"
  description        = "IAM role for ${each.key} Lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_policies" {
  for_each = local.lambda_definitions

  statement {
    sid = "CloudWatchLogging"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = ["arn:aws:logs:${var.region}:${var.account_id}:*"]
    effect    = "Allow"
  }

  statement {
    sid       = "DynamoDBAccess"
    actions   = each.value.dynamodb_actions
    resources = concat([var.dynamodb_table_arn], each.value.stream_access ? [var.dynamodb_table_stream_arn] : [])
    effect    = "Allow"
  }

  dynamic "statement" {
    for_each = var.error_alert_topic_arn != null && trimspace(var.error_alert_topic_arn) != "" ? [1] : []

    content {
      sid       = "SnsPublishAlerts"
      actions   = ["sns:Publish"]
      resources = [var.error_alert_topic_arn]
      effect    = "Allow"
    }
  }

  dynamic "statement" {
    for_each = each.value.release_notification_access && var.release_notification_topic_arn != null && trimspace(var.release_notification_topic_arn) != "" ? [1] : []

    content {
      sid       = "SnsPublishReleaseNotifications"
      actions   = ["sns:Publish"]
      resources = [var.release_notification_topic_arn]
      effect    = "Allow"
    }
  }
}

resource "aws_iam_role_policy" "lambda_policies" {
  for_each = local.lambda_definitions
  role     = aws_iam_role.lambda_roles[each.key].id
  policy   = data.aws_iam_policy_document.lambda_policies[each.key].json
}

resource "aws_s3_object" "lambda_objects" {
  for_each    = local.lambda_definitions
  bucket      = var.artifact_bucket_id
  key         = "${each.key}.zip"
  source      = "${each.key}.zip"
  source_hash = filemd5("${each.key}.zip")
}

resource "aws_lambda_function" "lambda_functions" {
  for_each         = local.lambda_definitions
  s3_bucket        = var.artifact_bucket_id
  s3_key           = aws_s3_object.lambda_objects[each.key].key
  function_name    = "${local.name_prefix}-${each.key}"
  description      = each.value.description
  role             = aws_iam_role.lambda_roles[each.key].arn
  handler          = "${each.key}.lambda_handler"
  runtime          = var.python_version
  timeout          = 90
  source_code_hash = filemd5("${each.key}.zip")

  environment {
    variables = merge(
      {
        environment                    = var.environment
        dynamodb_table_name            = var.dynamodb_table_name
        error_alert_topic_arn          = var.error_alert_topic_arn
        release_notification_topic_arn = var.release_notification_topic_arn
      },
      each.key == "apple_web_scrape" ? {
        dynamodb_table_name = var.dynamodb_table_name
      } : {}
    )
  }
}

output "lambda_function_arns" {
  value = { for name, fn in aws_lambda_function.lambda_functions : name => fn.arn }
}

output "lambda_function_names" {
  value = { for name, fn in aws_lambda_function.lambda_functions : name => fn.function_name }
}

output "lambda_schedules" {
  value = { for name, cfg in local.scheduled_lambdas : name => cfg.schedule }
}

output "lambda_functions" {
  value = {
    for name, fn in aws_lambda_function.lambda_functions : name => {
      name     = fn.function_name
      arn      = fn.arn
      schedule = try(local.lambda_definitions[name].schedule, null)
    }
  }
}
