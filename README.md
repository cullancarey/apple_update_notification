[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)]()
[![Terraform](https://img.shields.io/badge/Terraform-AWS-orange.svg)]()
[![CI/CD](https://github.com/cullancarey/apple_update_notification/actions/workflows/deploy_env.yaml/badge.svg)]()

# Apple Update Notification

Automated system that:

1. Scrapes Apple's public "Latest software releases" support page.
2. Stores the most recently observed OS versions (iOS, macOS, watchOS, tvOS, visionOS) in DynamoDB.
3. Publishes a tweet whenever a new release version is detected (via DynamoDB Streams → Lambda).

Infrastructure is provisioned with Terraform on AWS. Shared Python utilities (DynamoDB + SSM Parameter Store + Twitter auth) are packaged into a Lambda layer. Two core Lambda functions power the flow:

- `apple_web_scrape` – Periodically scrapes and updates DynamoDB if versions change.
- `apple_send_update` – Triggered by DynamoDB Stream events to tweet newly detected releases.

---

## High-Level Architecture

```
AWS Event / (Scheduled Trigger e.g. EventBridge) --> apple_web_scrape (Lambda)
	|  (GET https://support.apple.com/en-us/100100)
	v
Amazon DynamoDB (apple_os_updates_<env>) -- Stream --> apple_send_update (Lambda) -- Tweepy --> Twitter

Shared Lambda Layer: apple_utils (boto3 + tweepy + helper code)
```

Key Components:

- **DynamoDB Table**: `apple_os_updates_<environment>`; partition key: `device`. Stream enabled (NEW_IMAGE) for change detection.
- **Lambda Layer**: `apple_utils` (built from `apple_utils.py` + `requirements.txt`).
- **Parameter Store (SSM)**: Holds Twitter API credentials (see below).
- **IAM Roles/Policies**: Scoped to least privilege for CloudWatch Logs, DynamoDB access, S3 artifact retrieval, and SSM parameter reads.
- **S3 Bucket**: Stores zipped Lambda deployment packages and layer bundle.

---

## Repository Layout

```
├─ lambdas/
│  ├─ apple_web_scrape.py      # Scrapes Apple site, updates DynamoDB
│  ├─ apple_send_update.py     # Processes DynamoDB stream, posts tweets
│  ├─ apple_utils.py           # Shared utilities (DynamoDB, SSM, Tweepy auth)
│  ├─ apple_subscription.py    # (Placeholder)
│  ├─ apple_thank_you.py       # (Placeholder)
├─ terraform/                  # Infrastructure as code
│  ├─ *.tf                     # Providers, Lambdas, DynamoDB, IAM, etc.
├─ tests/                      # Pytest unit tests for both Lambdas
├─ create_lambda_package.sh    # Builds layer zip (apple_utils.zip)
├─ requirements.txt            # Runtime dependencies
├─ requirements-dev.txt        # Dev/testing dependencies
└─ README.md
```

---

## Lambda Functions

### apple_web_scrape
Responsibilities:
- Fetches `https://support.apple.com/en-us/100100`.
- Parses "The latest version of <OS> is X.Y.Z" style statements using BeautifulSoup & regex.
- Builds a structured dictionary: latest version per OS + tweet-ready release statements.
- Compares against existing DynamoDB item set; updates only changed entries (one item per device key: `device`).

Environment Variables:
- `dynamodb_table_name` – Name of DynamoDB table (injected by Terraform).

### apple_send_update
Responsibilities:
- Triggered by DynamoDB Stream (NEW_IMAGE) events.
- Filters for supported devices: iOS, macOS, watchOS, tvOS, visionOS.
- Extracts `ReleaseStatement` and posts a tweet via Tweepy.

Secrets (retrieved at runtime from SSM Parameter Store):
- `apple_update_notification_api_key`
- `apple_update_notification_secret_key`
- `apple_update_notification_twitter_access_token`
- `apple_update_notification_access_secret_token`

These parameter names are hard-coded with a `apple_update_notification` prefix in `apple_utils.py`.

---

## Twitter Integration

The Tweepy client is constructed per invocation (once) using credentials from decrypted SSM parameters. Make sure you have stored the above parameters (SecureString) in the same AWS region as the Lambda functions. Minimum required IAM action: `ssm:GetParameter` for each parameter ARN.

---

## Building the Lambda Layer

The layer contains:
- `apple_utils.py`
- Third-party libraries from `requirements.txt` (e.g., `boto3`, `tweepy`, `beautifulsoup4`, `urllib3` etc.)

Use the helper script:

```bash
./create_lambda_package.sh
```

This produces `apple_utils.zip` at the repository root, which Terraform uploads to S3 and attaches as a Lambda layer (`lambda_utils_layer`).

---

## Terraform Deployment

Variables (see `terraform/variables.tf`):

| Name | Description | Example |
|------|-------------|---------|
| `environment` | Deployment environment identifier | `develop`, `main` |
| `twitter_username` | Tag / identification only (not required for auth) | `my_twitter_handle` |

Core resources provisioned:
- DynamoDB table (with stream).
- Two Lambda functions + IAM roles & policies.
- Lambda layer from S3 object (`apple_utils.zip`).
- S3 bucket for artifacts & (optionally) static site / backups.

Backend configuration is split via `backend.main.conf` / `backend.develop.conf` to support multiple workspaces/environments.

### Typical Workflow
```bash
cd terraform
# (Optionally) select or create a workspace: terraform workspace select develop || terraform workspace new develop
terraform init -backend-config=backend.develop.conf
terraform plan -var="environment=develop" -var="twitter_username=<your_handle>"
terraform apply -var="environment=develop" -var="twitter_username=<your_handle>" -auto-approve
```

Assumptions:
- You have pre-built and uploaded (or allowed Terraform to upload) `apple_utils.zip` into the designated S3 bucket via `create_lambda_package.sh`.
- SSM parameters for Twitter credentials already exist.
- AWS credentials & default region (`us-east-2` primary) are configured locally.

---

## Local Development & Testing

Install development dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Run tests locally from /lambdas directory:
```bash
python -m pytest -v ../tests
```

The tests mock external services (HTTP, SSM, Twitter, DynamoDB) to enable deterministic fast feedback.

---

## Adding New Logic

1. Add or modify Lambda code under `lambdas/`.
2. If shared utilities are modified, rebuild the layer (`create_lambda_package.sh`) and re-apply Terraform so the new layer version is published and referenced.
3. Add / update unit tests in `tests/`.
4. Run `pytest` before committing.

---

## Operational Considerations

| Concern | Approach |
|---------|----------|
| Scheduling scrapes | Use EventBridge rule (not shown yet) to invoke `apple_web_scrape` periodically (e.g., every 15 min). |
| Idempotency | DynamoDB update only when versions differ; stream emits events only for changes. |
| Rate limits | Minimal HTTP calls; single page fetch per schedule. Twitter posting only on version changes. |
| Error handling | Extensive logging + guarded exception handling per record. Failed tweets won't halt entire batch. |
| Extensibility | Add more OS/device keys or downstream notifiers (email, SNS) by attaching new stream processors. |

---

## Environment & Parameters Summary

Environment Variables (Lambda):
- `dynamodb_table_name` (web scrape lambda)
- `website`, `environment` (various tagging/metadata variables)

SSM Secure Parameters (name → purpose):
- `apple_update_notification_api_key` – Twitter API key.
- `apple_update_notification_secret_key` – Twitter API secret.
- `apple_update_notification_twitter_access_token` – OAuth access token.
- `apple_update_notification_access_secret_token` – OAuth access secret.

All must be in the same region as the Lambda functions (primary: `us-east-2`).

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| No tweets posted | Missing or invalid SSM parameters | Verify parameter names & IAM `ssm:GetParameter` permissions. |
| Lambda layer import errors | Layer zip outdated | Re-run `create_lambda_package.sh` & redeploy Terraform. |
| DynamoDB updates never trigger | Scheduler not configured | Add EventBridge rule to invoke `apple_web_scrape`. |
| Parse failures / Missing devices | Apple page markup changed | Update CSS selectors & regex in `apple_web_scrape.parse_release_statements`. |

---

## Security Notes
- Store Twitter credentials only in SSM (SecureString); never commit secrets.
- Principle of least privilege for IAM policies (already scoped per service).
- Consider CloudWatch alarms on Lambda errors and DynamoDB throttling.

---

## Future Enhancements
- Public subscription API + email/webhook notifications.
- CloudFront + static site for status dashboard.
- Additional social platforms or Mastodon integration.
- Version diff summaries or CVE link enrichment.

---

## License
See `LICENSE` for details.

---

## Quick Reference Commands
```bash
# Build layer
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