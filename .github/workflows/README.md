# Workflows

CI/CD is split into reusable workflows and branch-trigger entry workflows.

## Files

- `plan.yaml` - Reusable workflow that builds Lambda artifacts, validates Terraform, runs Checkov, and executes `terraform plan`.
- `deploy.yaml` - Reusable workflow that builds Lambda artifacts, validates Terraform, runs Checkov, and executes `terraform apply`.
- `plan_env.yaml` - Trigger workflow for pull requests and manual dispatch; routes to plan for development or production.
- `deploy_env.yaml` - Trigger workflow for pushes to `develop` and `main`; routes to deploy for development or production.

## Environment Routing

- `develop` branch -> `development` environment/account.
- `main` branch -> `production` environment/account.

## Action Version Maintenance

To check latest releases for all external actions used here:

```bash
./check_action_releases.sh
```

When pinning by SHA, keep the tag as an inline comment for readability.