# Versioning Workflow Diagram

## Complete Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEVELOPER WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────┘

1. Feature Development
   ┌──────────────┐
   │   develop    │
   └──────┬───────┘
          │ git checkout -b feature/new-thing
          ▼
   ┌──────────────┐
   │ feature/...  │  ← Make changes
   └──────┬───────┘
          │ git commit -m "feat: add new thing"
          │ git push
          │ Create PR → develop
          ▼
   ┌──────────────────────────────────────────────────┐
   │  Pull Request Review & Merge to develop          │
   └──────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│               AUTOMATED CI/CD - DEVELOP BRANCH                       │
└─────────────────────────────────────────────────────────────────────┘

Push to develop triggers:

2. Semantic Release Workflow
   ┌──────────────────────────────────┐
   │  Analyze Commits                  │
   │  ├─ feat: → Minor bump (0.2.0)   │
   │  ├─ fix:  → Patch bump (0.1.1)   │
   │  └─ feat! → Major bump (1.0.0)   │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Create VERSION file              │
   │  Content: "0.2.0-beta.1"         │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Generate CHANGELOG.md            │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Create Git Tag                   │
   │  Tag: v0.2.0-beta.1              │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Create GitHub Pre-release        │
   │  With release notes              │
   └────────────┬─────────────────────┘
                │
                └──► Triggers Docker Workflow

3. Docker Build & Push Workflow
   ┌──────────────────────────────────┐
   │  Read VERSION file                │
   │  VERSION = "0.2.0-beta.1"        │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Get Git Info                     │
   │  COMMIT = "abc1234"              │
   │  BUILD = "dev"                   │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Build Docker Image               │
   │  --build-arg APP_VERSION=0.2.0-  │
   │              beta.1               │
   │  --build-arg APP_BUILD=dev       │
   │  --build-arg APP_COMMIT=abc1234  │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Tag & Push to Docker Hub         │
   │  ├─ develop                       │
   │  ├─ 0.2.0-beta.1                 │
   │  └─ 0.2.0-beta.1-abc1234         │
   └────────────┬─────────────────────┘
                │
                ▼
        Docker Hub Registry
   ┌──────────────────────────────────┐
   │  marcosvitol/                     │
   │  dunebugger-scheduler:develop    │
   └──────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│              PRODUCTION RELEASE - MAIN BRANCH                        │
└─────────────────────────────────────────────────────────────────────┘

4. Create PR: develop → main
   ┌──────────────┐       ┌──────────────┐
   │   develop    │  PR   │     main     │
   │  (0.2.0-β.1) │ ────► │   (0.1.0)    │
   └──────────────┘       └──────┬───────┘
                                 │
                          Review & Merge
                                 │
                                 ▼
                    Same CI/CD flow but with:
                    ├─ Production tags (no beta)
                    ├─ VERSION: "0.2.0"
                    ├─ Tag: v0.2.0
                    └─ Docker tags:
                        ├─ latest
                        ├─ 0.2.0
                        └─ 0.2.0-abc1234


┌─────────────────────────────────────────────────────────────────────┐
│                  RUNTIME - VERSION QUERY                             │
└─────────────────────────────────────────────────────────────────────┘

5. Application Runtime
   ┌──────────────────────────────────┐
   │  Docker Container Starts          │
   │  ENV:                             │
   │    APP_VERSION=0.2.0             │
   │    APP_BUILD=prod                │
   │    APP_COMMIT=abc1234            │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Python app/version.py            │
   │  Reads environment variables     │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Message Queue Handler            │
   │  Receives: get_version           │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌──────────────────────────────────┐
   │  Responds with:                   │
   │  {                                │
   │    "version": "0.2.0",           │
   │    "build": "prod",              │
   │    "commit": "abc1234",          │
   │    "full_version":               │
   │      "0.2.0-prod+abc1234"        │
   │  }                                │
   └──────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                    VERSION EVOLUTION                                 │
└─────────────────────────────────────────────────────────────────────┘

Commit History → Version Changes:

feat: add feature A          → 0.1.0
fix: bug fix B              → 0.1.1
feat: add feature C         → 0.2.0
fix: bug fix D              → 0.2.1
feat!: breaking change E    → 1.0.0
chore: update deps          → 1.0.0 (no change)


┌─────────────────────────────────────────────────────────────────────┐
│                    BRANCH STRATEGY                                   │
└─────────────────────────────────────────────────────────────────────┘

feature/xyz ──┐
              │ PR
feature/abc ──┼──► develop (v0.2.0-beta.1) ──┐
              │      │                         │ PR
bugfix/123 ───┘      │                         │
                     │                         ├──► main (v0.2.0)
                     ▼                         │        │
              Docker: develop                  │        │
              Beta releases                    │        ▼
              Testing environment              │   Docker: latest
                                              │   Production
                                              └────────┘
                                              When stable


┌─────────────────────────────────────────────────────────────────────┐
│                    DOCKER TAG MATRIX                                 │
└─────────────────────────────────────────────────────────────────────┘

Branch/Event        │ Tags Created
────────────────────┼──────────────────────────────────
develop             │ develop
                    │ 0.2.0-beta.1
                    │ 0.2.0-beta.1-abc1234
                    │
main                │ latest
                    │ 0.2.0
                    │ 0.2.0-abc1234
                    │
tag: v1.0.0         │ 1.0.0
                    │ 1.0.0-abc1234
                    │
PR #42              │ pr-42
