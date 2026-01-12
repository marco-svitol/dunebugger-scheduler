# First Deployment Checklist

Use this checklist for the initial setup and deployment of the automated versioning system.

## Pre-Deployment Setup

### 1. GitHub Repository Settings

- [ ] Navigate to repository Settings → Actions → General
- [ ] Under "Workflow permissions":
  - [ ] Select "Read and write permissions"
  - [ ] Check "Allow GitHub Actions to create and approve pull requests"
- [ ] Click "Save"

### 2. Docker Hub Setup

- [ ] Log in to [Docker Hub](https://hub.docker.com)
- [ ] Go to Account Settings → Security
- [ ] Click "New Access Token"
- [ ] Name it (e.g., "dunebugger-scheduler-github")
- [ ] Copy the access token (you won't see it again!)

### 3. GitHub Secrets Configuration

- [ ] Navigate to repository Settings → Secrets and variables → Actions
- [ ] Click "New repository secret"
- [ ] Add secret `DOCKER_HUB_USERNAME`:
  - Name: `DOCKER_HUB_USERNAME`
  - Value: Your Docker Hub username (e.g., `marcosvitol`)
- [ ] Add secret `DOCKER_HUB_ACCESS_TOKEN`:
  - Name: `DOCKER_HUB_ACCESS_TOKEN`
  - Value: The access token you just created
- [ ] Click "Add secret" for each

## First Commit & Push

### 4. Review Changes

- [ ] Review all modified and new files:
  ```bash
  git status
  ```

- [ ] Check the changes:
  ```bash
  git diff
  ```

### 5. Commit with Conventional Format

Choose the appropriate commit message:

**Option A: First feature (minor version)**
```bash
git add .
git commit -m "feat: implement automated versioning system

- Add semantic versioning with GitHub Actions
- Add Docker multi-environment support (dev/prod)
- Add version query endpoint in message queue
- Add comprehensive documentation"
git push origin 5-ntp-internet-conenction-check
```

**Option B: Build system update (patch version)**
```bash
git add .
git commit -m "build: add automated versioning and CI/CD pipelines

- Configure semantic-release for automatic version management
- Update Docker workflow for develop and main branches
- Add version information to application runtime"
git push origin 5-ntp-internet-conenction-check
```

### 6. Create Pull Request

- [ ] Go to GitHub repository
- [ ] Click "Pull requests" → "New pull request"
- [ ] Base: `develop` ← Compare: `5-ntp-internet-conenction-check`
- [ ] Title: "feat: implement automated versioning system"
- [ ] Fill in description
- [ ] Click "Create pull request"

## Verify Workflows

### 7. Check Workflow Execution

After merging to `develop`:

- [ ] Go to Actions tab in GitHub
- [ ] Verify "Semantic Release" workflow runs successfully
- [ ] Check that it created:
  - [ ] VERSION file in repository
  - [ ] Git tag (e.g., `v0.2.0-beta.1`)
  - [ ] GitHub pre-release

- [ ] Verify "Build and Push Docker Image" workflow runs
- [ ] Check that it pushed images to Docker Hub

### 8. Verify Docker Images

- [ ] Go to [Docker Hub](https://hub.docker.com/r/marcosvitol/dunebugger-scheduler/tags)
- [ ] Verify tags exist:
  - [ ] `develop`
  - [ ] Version tag (e.g., `0.2.0-beta.1`)
  - [ ] Version with commit (e.g., `0.2.0-beta.1-abc1234`)

### 9. Test Docker Image

Pull and test the image:

```bash
# Pull the develop image
docker pull marcosvitol/dunebugger-scheduler:develop

# Test version info
docker run --rm marcosvitol/dunebugger-scheduler:develop \
  python -c "from version import get_version_info; import json; print(json.dumps(get_version_info(), indent=2))"
```

Expected output:
```json
{
  "version": "0.2.0-beta.1",
  "build": "dev",
  "commit": "abc1234",
  "full_version": "0.2.0-beta.1-dev+abc1234"
}
```

- [ ] Verify output shows correct version information

## Production Release

### 10. Release to Production (When Ready)

- [ ] Test thoroughly on develop branch
- [ ] Create PR: `develop` → `main`
- [ ] Title: "Release v0.2.0" (or appropriate version)
- [ ] Review changes
- [ ] Merge PR

### 11. Verify Production Release

After merging to `main`:

- [ ] Check Actions tab for successful workflows
- [ ] Verify GitHub release was created (not pre-release)
- [ ] Check Docker Hub for tags:
  - [ ] `latest`
  - [ ] Version (e.g., `0.2.0`)
  - [ ] Version with commit (e.g., `0.2.0-abc1234`)

### 12. Test Production Image

```bash
# Pull latest
docker pull marcosvitol/dunebugger-scheduler:latest

# Test version
docker run --rm marcosvitol/dunebugger-scheduler:latest \
  python -c "from version import get_version_info; import json; print(json.dumps(get_version_info(), indent=2))"
```

Expected output:
```json
{
  "version": "0.2.0",
  "build": "prod",
  "commit": "abc1234",
  "full_version": "0.2.0-prod+abc1234"
}
```

- [ ] Verify `build` shows `"prod"`
- [ ] Verify version is correct

## Post-Deployment Verification

### 13. Test Version Query (Integration Test)

If you have a running instance:

- [ ] Send message queue command:
  ```
  Subject: scheduler.command.get_version
  Body: {}
  ```

- [ ] Verify response:
  ```
  Subject: scheduler.reply.version_info
  Body: {
    "version": "0.2.0",
    "build": "prod",
    "commit": "abc1234",
    "full_version": "0.2.0-prod+abc1234"
  }
  ```

### 14. Verify CHANGELOG

- [ ] Check that CHANGELOG.md was created in repository
- [ ] Review entries match commit history
- [ ] Verify version numbers are correct

## Troubleshooting

### Workflow Fails: "Resource not accessible by integration"

**Issue**: GitHub Actions doesn't have write permissions

**Fix**: 
1. Settings → Actions → General → Workflow permissions
2. Select "Read and write permissions"
3. Re-run workflow

### Workflow Fails: "No release published"

**Issue**: No commits since last release or wrong commit format

**Fix**:
- Ensure commits follow conventional format (feat:, fix:, etc.)
- Check that commits are new (after last tag)

### Docker Push Fails: "Authentication required"

**Issue**: Docker Hub credentials not configured

**Fix**:
1. Verify secrets DOCKER_HUB_USERNAME and DOCKER_HUB_ACCESS_TOKEN exist
2. Check token is valid on Docker Hub
3. Re-run workflow

### Version Shows Default Values

**Issue**: Environment variables not set in container

**Fix**:
- Ensure using image built by GitHub Actions
- Don't manually build without setting build args
- Check Docker build logs for ARG/ENV statements

## Success Criteria

✅ All workflows run without errors  
✅ VERSION file exists in repository  
✅ Git tags created automatically  
✅ Docker images pushed with correct tags  
✅ Version query returns correct information  
✅ CHANGELOG.md generated automatically  

## Next Steps

- [ ] Update deployment documentation
- [ ] Train team on commit message conventions
- [ ] Set up alerts for failed workflows
- [ ] Consider adding automated testing
- [ ] Document rollback procedures

## Resources

- [VERSIONING.md](../VERSIONING.md) - Complete versioning guide
- [COMMIT_CONVENTION.md](COMMIT_CONVENTION.md) - Commit format reference
- [WORKFLOW_DIAGRAM.md](WORKFLOW_DIAGRAM.md) - Visual workflow guide
- [semantic-release docs](https://semantic-release.gitbook.io/semantic-release/)
- [Conventional Commits](https://www.conventionalcommits.org/)
