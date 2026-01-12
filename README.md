# dunebugger-scheduler

Scheduler component for dunebugger

## Features

- Schedule interpretation and execution
- Message queue integration for remote control
- NTP status monitoring
- Automated version management and releases

## Documentation

- [Versioning and Release Guide](VERSIONING.md) - Complete guide for automated versioning, releases, and Docker builds

## Quick Start

### Pull Docker Image

```bash
# Latest production release
docker pull marcosvitol/dunebugger-scheduler:latest

# Development version
docker pull marcosvitol/dunebugger-scheduler:develop

# Specific version
docker pull marcosvitol/dunebugger-scheduler:1.2.3
```

### Check Version

Query version information via message queue:

```python
# Send message with subject "get_version"
# Response will contain version, build, commit, and full_version
```

## Development

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new feature      # Minor version bump
fix: fix bug              # Patch version bump
docs: update docs         # Patch version bump
chore: routine task       # No version bump
```

See [VERSIONING.md](VERSIONING.md) for complete details on versioning and releases.

## License

See [LICENSE](LICENSE) file for details.
