# GitHub Actions Workflows

This document describes the automated workflows configured for this repository.

## Overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| Test | Push/PR to `main` | Run tests and linting |
| Release | Manual dispatch | Manual semantic versioning and releases |
| Validate Commits | Pull requests | Ensure commit messages follow conventional commits |

## Workflows

### 1. Test (`test.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch

**Jobs:**

#### Test
- Runs on Python 3.13
- Installs dependencies from `requirements_test.txt`
- Executes pytest with coverage
- Uploads coverage to Codecov (if configured)

#### Lint
- Runs ruff linter
- Checks Black formatting
- Checks isort import sorting

#### Validate
- Validates JSON files (manifest, strings, translations)
- Checks for required integration files

**Required for:** Pull request approval

---

### 2. Release (`release.yml`)

**Triggers:**
- Manual trigger only (via GitHub Actions UI)
- Must be manually dispatched after tests pass

**Semantic Versioning Rules:**
- `feat` commits → Minor version bump (0.1.0 → 0.2.0)
- `fix`, `perf`, `docs`, `refactor` commits → Patch version bump (0.1.0 → 0.1.1)
- `BREAKING CHANGE` or `feat!` → Major version bump (0.1.0 → 1.0.0)
- Other types (`chore`, `test`, `ci`, etc.) → No release

**Automated Actions:**
1. Analyzes commit messages since last release
2. Determines next version number
3. Updates `manifest.json` with new version
4. Generates/updates `CHANGELOG.md`
5. Creates Git tag (e.g., `v0.2.0`)
6. Creates GitHub release with notes
7. Builds and attaches integration ZIP package
8. Commits changes back to repository

**Requirements:**
- Commits must follow [Conventional Commits](https://www.conventionalcommits.org/) format
- `GITHUB_TOKEN` (automatically provided)

---

### 3. Validate Commits (`validate-commits.yml`)

**Triggers:**
- Pull requests (opened, synchronized, reopened)

**Purpose:**
- Ensures all commits follow conventional commits format
- Validates commit message structure:
  - Type must be one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
  - Subject must not be empty
  - Header max length: 100 characters

**Example valid commits:**
```
feat: add support for humidity sensors
fix(coordinator): handle connection timeout gracefully
docs: update installation instructions
```

**Example invalid commits:**
```
Added new feature          # Missing type
feat add sensor            # Missing colon
FEAT: new sensor           # Type must be lowercase
```

---

## Dependabot

**Configuration:** `.github/dependabot.yml`

Automatically creates pull requests for:
- GitHub Actions updates (weekly)
- Python dependency updates (weekly)

All dependency updates use conventional commit format:
```
chore(deps): bump actions/checkout from 3 to 4
```

---

## Release Process

### Manual Release via GitHub Actions (Recommended)

1. Make changes and commit using conventional commits:
   ```bash
   git commit -m "feat: add new sensor type"
   git commit -m "fix: correct temperature conversion"
   ```

2. Merge your PR to `main` branch:
   - Ensure all tests pass
   - Merge approved pull request via GitHub UI
   - Or push directly to main (if you have permissions)

3. Manually trigger release workflow:
   - Go to GitHub Actions tab
   - Select "Release" workflow
   - Click "Run workflow" button
   - Select `main` branch
   - Click "Run workflow"

4. Release workflow will:
   - Determine version based on commits (e.g., 0.2.0)
   - Update manifest.json
   - Create CHANGELOG.md entry
   - Create Git tag and GitHub release
   - Build and attach ZIP package

### Manual Release via Git (Alternative)

If GitHub Actions is unavailable:

1. Update version in `manifest.json`
2. Update `CHANGELOG.md`
3. Create Git tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
4. Create release on GitHub with ZIP package

**Note:** Using semantic-release via GitHub Actions is preferred as it automates changelog and version management.

---

## Commit Message Examples

### New Feature (Minor Version)
```bash
git commit -m "feat: add support for exhaust fan speed control"
# Results in: 0.1.0 → 0.2.0
```

### Bug Fix (Patch Version)
```bash
git commit -m "fix: correct CO2 sensor readings"
# Results in: 0.1.0 → 0.1.1
```

### Breaking Change (Major Version)
```bash
git commit -m "feat!: change configuration format

BREAKING CHANGE: Configuration now uses YAML instead of JSON"
# Results in: 0.1.0 → 1.0.0
```

### Multiple Changes
```bash
git commit -m "feat: add humidity sensor support

- Add humidity sensor entity
- Add temperature sensor entity
- Update coordinator to handle sensor devices
- Add tests for sensor platform

Closes #123"
# Results in: 0.1.0 → 0.2.0
```

### Documentation Only (No Release)
```bash
git commit -m "docs: update installation instructions"
# No version change
```

---

## Troubleshooting

### Release Not Created

**Symptom:** Manually triggered release but no release was created

**Possible causes:**
1. Commits don't follow conventional commits format
2. All commits since last release are types that don't trigger releases (`chore`, `test`, `ci`, `style`)
3. No commits since last release

**Solution:**
- Check commit messages in GitHub
- Ensure at least one commit since last release has type `feat`, `fix`, or `BREAKING CHANGE`
- Check semantic-release logs in GitHub Actions for details

### Test Failure

**Symptom:** Tests fail in CI but pass locally

**Possible causes:**
1. Missing dependencies in `requirements_test.txt`
2. Python version differences
3. Environment-specific issues

**Solution:**
- Run tests with specific Python version: `python3.13 -m pytest`
- Check GitHub Actions logs for details

### Commit Validation Failed

**Symptom:** PR shows "validate commits" check failed

**Solution:**
- Rewrite commit messages to follow conventional commits
- Use interactive rebase to fix commit messages:
  ```bash
  git rebase -i HEAD~3  # Adjust number as needed
  # Change 'pick' to 'reword' for commits to fix
  ```

---

## Configuration Files

- `.releaserc.json` - Semantic release configuration
- `.commitlintrc.json` - Commit message linting rules
- `pyproject.toml` - Python tool configuration (Black, isort, Ruff, pytest)
- `scripts/update_version.py` - Version update script for releases
