# Terraform

Root Terraform stack for Apple Update Notification infrastructure.

## Current Design

The root stack composes four modules:

- `modules/data-store` - DynamoDB table and stream.
- `modules/storage` - Artifact S3 bucket and bucket security controls.
- `modules/lambda-service` - Lambda functions, IAM roles/policies, deployment artifacts, and stream mapping.
- `modules/observability` - CloudWatch log groups, EventBridge schedule rule/target, and Lambda invoke permissions.

## Environment Model

- Valid `environment` values are `development` and `production`.
- Backend configs:
  - `backend.develop.conf`
  - `backend.main.conf`
- S3 backend uses `use_lockfile = true` and `encrypt = true`.

## Common Commands

From repo root:

```bash
terraform -chdir=terraform init -backend-config=backend.develop.conf
terraform -chdir=terraform validate -no-color
terraform -chdir=terraform plan -var-file=develop.tfvars
```

If already inside this directory, remove `-chdir=terraform`.

## Production State Key Migration

If production state previously lived at `apple_update_notification.tfstate`,
run this one-time migration before using the new backend key
`apple_update_notification/production/terraform.tfstate`.

From this folder:

```bash
chmod +x migrate_prod_state_key.sh
./migrate_prod_state_key.sh --dry-run
./migrate_prod_state_key.sh
terraform init -reconfigure -backend-config=backend.main.conf
terraform plan -var-file=main.tfvars -no-color
```

Notes:

- The script makes a timestamped backup under `migration-backups/`.
- Use `--force` only if you intentionally want to overwrite an existing new key.
- Do not delete the old key until a successful plan/apply confirms state is healthy.

## Inputs/Outputs

Key inputs are defined in `variables.tf` (`environment`, `twitter_username`, `aws_region`).
Key outputs are defined in `outputs.tf` (DynamoDB table name, Lambda ARNs, artifact bucket name).