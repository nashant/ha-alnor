# Contributing to Alnor Integration

Thank you for your interest in contributing to the Alnor Home Assistant integration!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/nashant/ha-alnor.git
   cd ha-alnor
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements_test.txt
   ```

3. Run tests:
   ```bash
   pytest
   ```

## Commit Message Guidelines

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated semantic versioning and changelog generation.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: A new feature (triggers minor version bump)
- **fix**: A bug fix (triggers patch version bump)
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (whitespace, formatting)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement (triggers patch version bump)
- **test**: Adding or updating tests
- **build**: Changes to build system or dependencies
- **ci**: Changes to CI configuration
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

### Examples

```bash
# Feature (minor version bump: 0.1.0 -> 0.2.0)
git commit -m "feat: add support for humidity sensors"

# Bug fix (patch version bump: 0.1.0 -> 0.1.1)
git commit -m "fix: correct temperature reading conversion"

# Breaking change (major version bump: 0.1.0 -> 1.0.0)
git commit -m "feat!: change configuration format

BREAKING CHANGE: Configuration structure has changed. Users must update their config."

# Multiple types
git commit -m "feat(fan): add preset mode support

- Add new preset modes: eco, turbo
- Update fan entity configuration
- Add tests for preset modes"

# With scope
git commit -m "fix(sensor): handle missing temperature data gracefully"
```

### Breaking Changes

To trigger a major version bump, add `!` after the type or include `BREAKING CHANGE:` in the footer:

```bash
git commit -m "feat!: remove deprecated API methods"

# OR

git commit -m "refactor: update API client

BREAKING CHANGE: The connect() method now requires authentication parameters."
```

## Pull Request Process

1. **Create a feature branch** from `develop`:
   ```bash
   git checkout -b feat/my-feature develop
   ```

2. **Make your changes** and commit using conventional commit format

3. **Run tests** to ensure everything passes:
   ```bash
   pytest
   ```

4. **Push your branch** and create a pull request to `develop`

5. **Wait for CI checks** to pass:
   - Tests must pass on Python 3.11 and 3.12
   - Commit messages must follow conventional commits format
   - Code must pass linting checks

6. **Request a review** from maintainers

7. Once approved, your PR will be merged into `develop`

## Release Process

Releases are **fully automated** using semantic versioning:

1. When commits are merged to `main`, the release workflow analyzes commit messages

2. Based on commit types, it determines the version bump:
   - `feat` → minor version (0.1.0 → 0.2.0)
   - `fix`, `perf`, `docs`, `refactor` → patch version (0.1.0 → 0.1.1)
   - `BREAKING CHANGE` or `feat!` → major version (0.1.0 → 1.0.0)

3. The workflow automatically:
   - Bumps version in `manifest.json`
   - Generates/updates `CHANGELOG.md`
   - Creates a Git tag
   - Creates a GitHub release with zip package
   - Commits version changes back to the repository

**You don't need to manually update versions or create releases!**

## Testing

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_coordinator.py -v
```

### Run with Coverage
```bash
pytest --cov=custom_components.alnor --cov-report=html
```

### Run Linting
```bash
# Check code formatting
black --check custom_components/ tests/

# Check import sorting
isort --check-only custom_components/ tests/

# Run ruff linter
ruff check custom_components/ tests/
```

## Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use type hints where appropriate
- Write docstrings for public functions and classes

## Questions?

If you have questions or need help, please:
- Open an [issue](https://github.com/nashant/ha-alnor/issues)
- Check existing [discussions](https://github.com/nashant/ha-alnor/discussions)

Thank you for contributing! 🎉
