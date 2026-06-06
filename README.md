[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)]()
[![Terraform](https://img.shields.io/badge/Terraform-AWS-orange.svg)]()
[![CI/CD](https://github.com/cullancarey/apple_update_notification/actions/workflows/deploy_env.yaml/badge.svg)]()

# Apple Update Notification

This project automatically tracks Apple OS release changes and publishes updates to Twitter/X.

Current flow:

1. `apple_web_scrape` runs on an EventBridge schedule and scrapes Apple's release page.
2. Release data is written to DynamoDB (`apple_os_updates_<environment>`).
3. DynamoDB stream changes trigger `apple_send_update`.
4. `apple_send_update` formats and posts updates with Tweepy.

## Architecture Snapshot

```text
EventBridge schedule -> Lambda (apple_web_scrape)
					 -> DynamoDB table + stream
					 -> Lambda (apple_send_update)
					 -> Twitter/X API
```

Infrastructure is managed with Terraform modules in `terraform/modules`.
Python dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`).

## Repository Map

- `.github/` - GitHub Actions and workflow docs.
- `lambdas/` - Lambda handlers and shared runtime utilities.
- `terraform/` - Root Terraform stack and module composition.
- `tests/` - Pytest tests for Lambda behavior.

Each directory now has its own README with details about ownership and usage.

## Local Commands

Sync dependencies:

```bash
uv sync --group dev
```

Build Lambda packages:

```bash
./create_lambda_package.sh
```

Run tests:

```bash
uv run pytest -v
```

Validate Terraform:

```bash
terraform -chdir=terraform validate -no-color
```

## Deployment Model

- `develop` branch deploys to development account (`693590665244`).
- `main` branch deploys to production account (`651295191577`).
- Terraform enforces account/environment guardrails with `allowed_account_ids` and validated environment values.

## Notes

- Lambda artifacts are uploaded as zipped packages (`apple_web_scrape.zip`, `apple_send_update.zip`).
- Artifact bucket has versioning enabled plus lifecycle expiration for current and noncurrent objects after 60 days.
- CloudWatch log retention is environment-aware (development: 180 days, production: 365 days).

## License

See `LICENSE`.

## Quick Reference Commands
```bash
# Build Lambda packages
./create_lambda_package.sh

# Run tests
pytest -v

# Terraform deploy (develop)
cd terraform
terraform init -backend-config=backend.develop.conf
terraform apply -var="environment=develop" -var="twitter_username=<handle>"
```

---

Happy monitoring! Feel free to open issues or PRs with improvements.