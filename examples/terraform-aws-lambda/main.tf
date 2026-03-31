terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.38"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Build a canonical zip of the Lambda source and compute its hash.
# Because canonzip produces deterministic output, the hash only changes
# when the source files actually change.
data "external" "lambda_package" {
  program = ["canonzip", "zip", "--json", "${path.module}/lambda.zip", "${path.module}/src"]
}

resource "aws_iam_role" "lambda" {
  name = "canonzip-example-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_lambda_function" "this" {
  function_name    = "canonzip-example"
  filename         = "${path.module}/lambda.zip"
  source_code_hash = data.external.lambda_package.result.hash
  handler          = "handler.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda.arn
}
