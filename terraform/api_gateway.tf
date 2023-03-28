#############################################
#########subscription_intake_api#####################
#############################################

resource "aws_apigatewayv2_api" "subscription_intake_api" {
  name          = "subscription_intake_api"
  protocol_type = "HTTP"
  description   = "API gateway resource for intake of the subscription for on ${var.root_domain_name}"

}



resource "aws_apigatewayv2_domain_name" "subscription_intake_api_domain" {
  domain_name = var.subscription_intake_api_domain

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.subscription_intake_api_certificate.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}


resource "aws_apigatewayv2_stage" "subscription_intake_api_stage" {
  api_id      = aws_apigatewayv2_api.subscription_intake_api.id
  name        = "$default"
  description = "Stage for api gateway resource that intakes the websites subscription form."
  auto_deploy = true
}


resource "aws_apigatewayv2_api_mapping" "subscription_intake_api_mapping" {
  api_id      = aws_apigatewayv2_api.subscription_intake_api.id
  domain_name = aws_apigatewayv2_domain_name.subscription_intake_api_domain.id
  stage       = aws_apigatewayv2_stage.subscription_intake_api_stage.id
}


resource "aws_apigatewayv2_integration" "subscription_intake_api_integration" {
  api_id                 = aws_apigatewayv2_api.subscription_intake_api.id
  description            = "Integration for form intake api and form intake lambda."
  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.apple_update_notification_lambda.invoke_arn
  payload_format_version = "2.0"
}


resource "aws_apigatewayv2_route" "subscription_intake_api_route" {
  api_id    = aws_apigatewayv2_api.subscription_intake_api.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.subscription_intake_api_integration.id}"
}
