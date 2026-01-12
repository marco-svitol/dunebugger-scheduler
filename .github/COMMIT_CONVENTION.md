# Commit Message Quick Reference

## Format
```
<type>(<scope>): <subject>
```

## Types

| Type | Version | Description | Example |
|------|---------|-------------|---------|
| `feat` | MINOR | New feature | `feat: add temperature monitoring` |
| `fix` | PATCH | Bug fix | `fix: correct schedule parsing` |
| `perf` | PATCH | Performance improvement | `perf: optimize message processing` |
| `docs` | PATCH | Documentation only | `docs: update API examples` |
| `style` | PATCH | Code style (formatting, etc.) | `style: fix indentation` |
| `refactor` | PATCH | Code restructuring | `refactor: simplify mqueue handler` |
| `test` | PATCH | Add/modify tests | `test: add version handler tests` |
| `build` | PATCH | Build system changes | `build: update dependencies` |
| `ci` | PATCH | CI/CD changes | `ci: add docker cache` |
| `chore` | NONE | Maintenance tasks | `chore: update .gitignore` |

## Breaking Changes

Add `!` after type or `BREAKING CHANGE:` in footer for MAJOR version:

```
feat!: redesign API

BREAKING CHANGE: Message format changed
```

## Scopes (Optional)

```
feat(mqueue): add new message handler
fix(scheduler): correct time calculation
docs(readme): add installation steps
```

## Multi-line

```bash
git commit -m "feat: add version endpoint" -m "This adds a new endpoint to query version info via message queue"
```

## Examples

```bash
# Minor release (new feature)
git commit -m "feat: add NTP status monitoring"

# Patch release (bug fix)
git commit -m "fix: prevent null pointer in schedule interpreter"

# Patch release (docs)
git commit -m "docs: add API documentation"

# No release (chore)
git commit -m "chore: update dependency versions"

# Major release (breaking change)
git commit -m "feat!: change message queue protocol" -m "BREAKING CHANGE: All messages now require authentication header"
```
