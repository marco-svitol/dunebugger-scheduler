# Implementation Summary: Automated Versioning System

## Overview
Implemented a comprehensive automated versioning system with GitHub Actions workflows, Docker integration, and message queue version queries.

## Files Created

### 1. `/app/version.py`
- Central version management module
- Reads version from environment variables (set during Docker build)
- Provides `get_version_info()` and `get_version_string()` functions
- Default version: `0.1.0-dev`

### 2. `/VERSION`
- Plain text file containing current version
- Created/updated by semantic-release workflow
- Used by Docker workflow to determine version

### 3. `/.github/workflows/semantic-release.yml`
- Automated semantic versioning workflow
- Analyzes commit messages for version bumps
- Creates Git tags and GitHub releases
- Generates CHANGELOG.md
- Runs on push to `main` (stable) and `develop` (beta)

### 4. `/.github/COMMIT_CONVENTION.md`
- Quick reference guide for commit message format
- Lists all commit types and their version impact
- Includes examples for common scenarios

### 5. `/VERSIONING.md`
- Complete documentation for versioning system
- Explains workflows, commit conventions, and release process
- Includes troubleshooting guide
- Docker image usage examples

## Files Modified

### 1. `/app/mqueue_handler.py`
- Added `from version import get_version_info` import
- Added `get_version` subject handler in `process_mqueue_message()`
- Implemented `handle_get_version()` method to respond with version info

### 2. `/.github/workflows/docker-build-push.yml`
- Complete rewrite to support develop and main branches
- Extracts version from VERSION file
- Determines build type based on branch/tag
- Generates appropriate Docker tags:
  - `main`: `latest`, `<version>`, `<version>-<commit>`
  - `develop`: `develop`, `<version>-beta`, `<version>-<commit>`
- Passes version info as build arguments

### 3. `/Dockerfile`
- Added build arguments: `APP_VERSION`, `APP_BUILD`, `APP_COMMIT`
- Added environment variables to expose version info to app
- Version info available to Python app via `os.environ`

### 4. `/.gitignore`
- Added entries for semantic-release artifacts
- Prevents committing node_modules, CHANGELOG.md (auto-generated)

### 5. `/README.md`
- Updated with versioning information
- Added links to VERSIONING.md documentation
- Included Docker usage examples
- Added commit convention reference

## How It Works

### 1. Development Workflow

**Develop Branch (Pre-releases)**:
1. Developer creates feature branch from `develop`
2. Makes commits using conventional commit format
3. Creates PR to `develop`
4. On merge to `develop`:
   - Semantic Release workflow runs
   - Creates beta pre-release (e.g., `v1.2.3-beta.1`)
   - Docker workflow builds image with tags: `develop`, `1.2.3-beta.1`

**Main Branch (Production)**:
1. Create PR from `develop` to `main`
2. On merge to `main`:
   - Semantic Release workflow runs
   - Creates production release (e.g., `v1.2.3`)
   - Docker workflow builds image with tags: `latest`, `1.2.3`, `1.2.3-abc1234`

### 2. Version Information Flow

```
Commit Messages → Semantic Release → VERSION file → Docker Build Args → ENV vars → Python App
```

1. Commit messages determine version bump
2. Semantic Release creates VERSION file and Git tag
3. Docker workflow reads VERSION file
4. Builds image with version as build arguments
5. Dockerfile sets environment variables
6. Python app reads from environment

### 3. Querying Version

**Via Message Queue**:
```python
# Send message
{
  "subject": "scheduler.command.get_version",
  "body": {}
}

# Receive response
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

**Programmatically**:
```python
from version import get_version_info
info = get_version_info()
```

## Commit Message Impact

| Commit Type | Example | Version Change |
|-------------|---------|----------------|
| `feat:` | `feat: add new feature` | 0.1.0 → 0.2.0 |
| `fix:` | `fix: correct bug` | 0.1.0 → 0.1.1 |
| `feat!:` | `feat!: breaking change` | 0.1.0 → 1.0.0 |
| `chore:` | `chore: update deps` | No change |

## Docker Image Tags

### Production (main branch)
- `marcosvitol/dunebugger-scheduler:latest`
- `marcosvitol/dunebugger-scheduler:1.2.3`
- `marcosvitol/dunebugger-scheduler:1.2.3-abc1234`

### Development (develop branch)
- `marcosvitol/dunebugger-scheduler:develop`
- `marcosvitol/dunebugger-scheduler:1.2.3-beta.1`
- `marcosvitol/dunebugger-scheduler:1.2.3-beta.1-abc1234`

## Required GitHub Setup

### Secrets
1. `DOCKER_HUB_USERNAME` - Docker Hub username
2. `DOCKER_HUB_ACCESS_TOKEN` - Docker Hub access token

### Repository Settings
- Settings → Actions → General → Workflow permissions
- Enable "Read and write permissions"
- Enable "Allow GitHub Actions to create and approve pull requests"

## Testing the Implementation

### 1. Test Version Endpoint (Local)
```python
python -c "from app.version import get_version_info; print(get_version_info())"
```

### 2. Test in Docker Container
```bash
# Build with version info
docker build \
  --build-arg APP_VERSION=1.0.0 \
  --build-arg APP_BUILD=test \
  --build-arg APP_COMMIT=abc1234 \
  -t test-scheduler .

# Check version
docker run test-scheduler python -c "from version import get_version_info; print(get_version_info())"
```

### 3. Test Semantic Release (Dry Run)
```bash
# Install dependencies
npm install -g semantic-release @semantic-release/git @semantic-release/github

# Dry run (doesn't create release)
npx semantic-release --dry-run
```

## Next Steps

1. **First Release**: Make a commit to `develop` using conventional format:
   ```bash
   git add .
   git commit -m "feat: implement automated versioning system"
   git push
   ```

2. **Verify Workflows**: Check GitHub Actions tab for workflow runs

3. **Test Version Query**: Send `get_version` message to running container

4. **Production Release**: When ready, merge `develop` to `main`

## Benefits

✅ **Automated Version Management**: No manual version updates needed
✅ **Consistent Docker Tags**: Clear separation between dev and prod
✅ **Version Visibility**: Query version at runtime via message queue
✅ **Audit Trail**: CHANGELOG.md auto-generated from commits
✅ **Reproducible Builds**: Each build tagged with commit SHA
✅ **Clear Release Process**: Well-defined workflow for releases
