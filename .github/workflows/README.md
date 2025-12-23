# GitHub Actions CI/CD Pipeline

## Overview

This repository uses GitHub Actions for continuous integration and deployment.

## Workflows

### `ci.yml` - Main CI/CD Pipeline

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

1. **build_and_test**
   - Runs on every push and PR
   - Lints code with flake8
   - Runs all 60+ tests
   - Generates coverage reports
   - Builds Docker images

2. **deploy_production**
   - Runs only on push to `main` branch
   - Deploys to production server via SSH
   - Runs database migrations
   - Restarts systemd services

3. **deploy_staging**
   - Runs only on push to `develop` branch
   - Deploys to staging server via SSH
   - Same steps as production

## Required Secrets

Configure these in GitHub Settings → Secrets and variables → Actions:

### Testing
- `GEMINI_API_KEY_TEST` (optional) - Test API key for CI

### Production
- `PROD_HOST` - Production server IP/hostname
- `PROD_USERNAME` - SSH username
- `PROD_SSH_KEY` - Private SSH key
- `PROD_SSH_PORT` (optional) - SSH port, defaults to 22

### Staging (optional)
- `STAGING_HOST` - Staging server IP/hostname
- `STAGING_USERNAME` - SSH username
- `STAGING_SSH_KEY` - Private SSH key
- `STAGING_SSH_PORT` (optional) - SSH port, defaults to 22

## Workflow Diagram

```
Push to main/develop
    ↓
Build and Test
    ├─ Lint
    ├─ Run Tests (60+)
    ├─ Coverage Report
    └─ Build Docker
    ↓
Deploy (if on main/develop)
    ├─ Pull Code
    ├─ Install Dependencies
    ├─ Run Migrations
    └─ Restart Services
```

## Status Badges

Add to your README.md:

```markdown
![CI/CD](https://github.com/yourusername/auramail/workflows/CI%2FCD%20Pipeline/badge.svg)
![Coverage](https://codecov.io/gh/yourusername/auramail/branch/main/graph/badge.svg)
```








