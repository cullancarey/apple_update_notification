# Terraform Modules

Reusable infrastructure modules used by the root Terraform stack.

## Modules

- `data-store` - DynamoDB table for release state and stream output.
- `storage` - S3 artifact bucket with public-block, encryption, lifecycle, and TLS-only policy.
- `lambda-service` - Lambda compute resources, IAM permissions, S3 objects for code artifacts, and stream event mapping.
- `observability` - Log groups and scheduled invocation wiring.

Each module has its own README describing inputs/outputs and resource behavior.