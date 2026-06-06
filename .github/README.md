# .github

This directory contains GitHub automation config for planning and deploying infrastructure.

## Contents

- `workflows/` - Reusable and entrypoint workflows for plan/deploy pipelines.

## Operational Notes

- Workflows use OIDC (`id-token: write`) and assume AWS roles at runtime.
- Lambda deployment artifacts are built in CI and passed to Terraform jobs as workflow artifacts.
- Action release checks can be run locally with `./check_action_releases.sh` from repo root.