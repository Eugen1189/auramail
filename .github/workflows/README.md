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
   - Runs all 291+ tests with parallel execution
   - Generates coverage reports (83%+ coverage)
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

## Required Dependencies

### Pytest Plugins

The project requires the following pytest plugins for parallel execution and test ordering:

- `pytest-xdist>=3.3.0` - For parallel test execution (`-n auto`)
- `pytest-order>=1.1.0` - For test ordering (`--order-scope=module`)
- `pytest-cov>=4.1.0` - For coverage reporting (already in requirements.txt)

**Installation:**
```bash
pip install -r requirements.txt
# Or explicitly:
pip install pytest-xdist pytest-order pytest-cov
```

**Why these plugins?**

The `pytest.ini` configuration file uses:
- `-n auto` - Requires `pytest-xdist` for parallel execution
- `--order-scope=module` - Requires `pytest-order` for test ordering
- `--dist loadscope` - Requires `pytest-xdist` for process isolation

If these plugins are not installed, pytest will fail with:
```
ERROR: unrecognized arguments: -n auto --order-scope=module
```

## CI/CD Configuration

The CI workflow (`ci.yml`) explicitly installs these plugins in the "Install Dependencies" step:

```yaml
- name: Install Dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    # CRITICAL: Explicitly install pytest plugins required by pytest.ini
    pip install pytest-xdist pytest-order pytest-cov
```

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
    ├─ Install Dependencies (including pytest-xdist, pytest-order)
    ├─ Lint
    ├─ Run Tests (291+) in parallel
    ├─ Coverage Report (83%+)
    └─ Build Docker
    ↓
Deploy (if on main/develop)
    ├─ Pull Code
    ├─ Install Dependencies
    ├─ Run Migrations
    └─ Restart Services
```

## Test Execution

Tests run in parallel using `pytest-xdist`:
- `-n auto` - Automatically determines number of processes based on CPU cores
- `--dist loadscope` - Ensures tests within the same class run in the same process
- `--order-scope=module` - Ensures proper test execution order

This configuration provides:
- **Faster execution** - Tests run in parallel across multiple CPU cores
- **Better isolation** - Each process gets its own database instance
- **Consistent ordering** - Tests execute in a predictable order

## Status Badges

Add to your README.md:

```markdown
![CI/CD](https://github.com/yourusername/auramail/workflows/CI%2FCD%20Pipeline/badge.svg)
![Coverage](https://codecov.io/gh/yourusername/auramail/branch/main/graph/badge.svg)
```

## Troubleshooting

### "unrecognized arguments: -n auto"

**Problem:** pytest-xdist is not installed.

**Solution:**
```bash
pip install pytest-xdist pytest-order pytest-cov
```

### "unrecognized arguments: --order-scope=module"

**Problem:** pytest-order is not installed.

**Solution:**
```bash
pip install pytest-order
```

### Tests fail in CI but pass locally

**Possible causes:**
1. Missing pytest plugins in CI environment
2. Different Python version
3. Missing environment variables

**Solution:** Check CI logs and ensure all dependencies are installed in the "Install Dependencies" step.
