# Versioning and Release Guide

## Overview

This project uses automated semantic versioning and CI/CD workflows to manage releases and Docker image builds.

## Versioning System

### Semantic Versioning

The project follows [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Commit Types and Version Impact

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement | PATCH |
| `docs` | Documentation changes | PATCH |
| `style` | Code style changes | PATCH |
| `refactor` | Code refactoring | PATCH |
| `test` | Test additions/changes | PATCH |
| `build` | Build system changes | PATCH |
| `ci` | CI/CD changes | PATCH |
| `chore` | Other changes | No release |
| `BREAKING CHANGE` | Breaking changes (in footer) | MAJOR |

#### Examples

```bash
# Minor version bump (new feature)
feat: add NTP status monitoring

# Patch version bump (bug fix)
fix: correct schedule parsing error

# Major version bump (breaking change)
feat!: redesign message queue API

BREAKING CHANGE: The mqueue message format has changed.
All clients must update to the new format.

# No version bump
chore: update dependencies
```

## Workflows

### 1. Semantic Release Workflow

**File**: `.github/workflows/semantic-release.yml`

**Triggers**:
- Push to `main` branch (production releases)
- Push to `develop` branch (beta pre-releases)

**What it does**:
1. Analyzes commit messages since last release
2. Determines next version number
3. Generates CHANGELOG.md
4. Creates VERSION file
5. Creates Git tag (e.g., `v1.2.3`)
6. Creates GitHub release with release notes

**Branch Behavior**:
- **main**: Creates stable releases (e.g., `v1.2.3`)
- **develop**: Creates pre-releases (e.g., `v1.2.3-beta.1`)

### 2. Docker Build & Push Workflow

**File**: `.github/workflows/docker-build-push.yml`

**Triggers**:
- Push to `main` or `develop` branches
- Git tags starting with `v*`
- Pull requests to `main` or `develop`
- After successful semantic release

**Docker Image Tags**:

| Branch/Event | Tags Created | Example |
|--------------|--------------|---------|
| **main** | `latest`, `<version>`, `<version>-<commit>` | `latest`, `1.2.3`, `1.2.3-abc1234` |
| **develop** | `develop`, `<version>`, `<version>-<commit>` | `develop`, `1.2.3-beta.1`, `1.2.3-beta.1-abc1234` |
| **tags** | `<version>`, `<version>-<commit>` | `1.2.3`, `1.2.3-abc1234` |
| **PRs** | `pr-<number>` | `pr-42` |

**Build Arguments**:
The workflow injects version information into the Docker image:
- `APP_VERSION`: Semantic version (e.g., `1.2.3`)
- `APP_BUILD`: Build type (`prod`, `dev`, `release`, `branch`)
- `APP_COMMIT`: Short commit SHA (e.g., `abc1234`)

## Version Information in Application

### Querying Version via Message Queue

Send a message with subject `get_version`:

```python
# Request
{
  "subject": "scheduler.command.get_version",
  "body": {}
}

# Response
{
  "subject": "scheduler.reply.version_info",
  "body": {
    "version": "1.2.3",
    "build": "prod",
    "commit": "abc1234",
    "full_version": "1.2.3-prod+abc1234"
  }
}
```

### Programmatic Access

```python
from version import get_version_info, get_version_string

# Get full version info
info = get_version_info()
# Returns: {
#   "version": "1.2.3",
#   "build": "prod",
#   "commit": "abc1234",
#   "full_version": "1.2.3-prod+abc1234"
# }

# Get version string
version_str = get_version_string()
# Returns: "1.2.3-prod+abc1234"
```

## Release Workflow

### For Feature Development

1. Create feature branch from `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-new-feature
   ```

2. Make changes and commit using conventional commits:
   ```bash
   git add .
   git commit -m "feat: add new awesome feature"
   ```

3. Push and create PR to `develop`:
   ```bash
   git push -u origin feature/my-new-feature
   ```

4. After PR is merged to `develop`:
   - Semantic Release creates a beta pre-release
   - Docker image is built with `develop` tag
   - Example: `marcosvitol/dunebugger-scheduler:develop`

### For Production Release

1. Create PR from `develop` to `main`

2. After PR is merged to `main`:
   - Semantic Release creates a production release
   - Docker image is built with `latest` and version tags
   - Example tags:
     - `marcosvitol/dunebugger-scheduler:latest`
     - `marcosvitol/dunebugger-scheduler:1.2.3`
     - `marcosvitol/dunebugger-scheduler:1.2.3-abc1234`

## Docker Image Usage

### Pull Latest Production Image
```bash
docker pull marcosvitol/dunebugger-scheduler:latest
```

### Pull Specific Version
```bash
docker pull marcosvitol/dunebugger-scheduler:1.2.3
```

### Pull Development Image
```bash
docker pull marcosvitol/dunebugger-scheduler:develop
```

### Check Version in Running Container
```bash
docker exec <container-name> python -c "from version import get_version_string; print(get_version_string())"
```

## Initial Setup

### Required GitHub Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

1. `DOCKER_HUB_USERNAME`: Your Docker Hub username
2. `DOCKER_HUB_ACCESS_TOKEN`: Docker Hub access token (create at hub.docker.com → Account Settings → Security)

### Repository Permissions

The semantic-release workflow needs write permissions:
- Go to Settings → Actions → General → Workflow permissions
- Select "Read and write permissions"
- Check "Allow GitHub Actions to create and approve pull requests"

## Troubleshooting

### Release Not Created

**Problem**: Commits pushed but no release created.

**Solution**: Ensure commits follow conventional commit format:
```bash
# ✅ Good - will trigger release
git commit -m "fix: correct typo in config"

# ❌ Bad - will not trigger release
git commit -m "fixed typo"
```

### Docker Build Failed

**Problem**: Docker workflow fails on version extraction.

**Solution**: Ensure VERSION file exists or workflow will default to `0.1.0`.

### Version Not Available in App

**Problem**: `get_version` returns default values.

**Solution**: 
1. Check environment variables are set in Docker run:
   ```bash
   docker run -e APP_VERSION=1.2.3 -e APP_BUILD=prod -e APP_COMMIT=abc1234 ...
   ```
2. Or rebuild image with proper build args (handled automatically by workflow)

## Manual Version Override

If needed, you can manually create a VERSION file:

```bash
echo "1.2.3" > VERSION
git add VERSION
git commit -m "chore: set version to 1.2.3"
git push
```

## References

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [semantic-release](https://github.com/semantic-release/semantic-release)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
