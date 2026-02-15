# Oasis Real Estate Simulation - Development Guide

## 1. Environment Setup

- **Python Version**: 3.10+
- **Encoding**: UTF-8 (Strictly Enforced)

All files **MUST** be saved with UTF-8 encoding.
If you encounter `UnicodeDecodeError`, convert the file immediately.

## 2. Code Quality Standards (CI/CD)

This project uses **Strict Linting** to ensure code quality and consistency.
The following tools run automatically on every `git push`:

### A. Tools Used

1. **Ruff**: Fast, modern linter (replaces flake8 for complex checks).
1. **Flake8**: Classic Python linter.
1. **Black / Isort**: Code formatter and import sorter.
1. **Mdformat**: Markdown formatter.

### B. Pre-commit Hooks

To catch errors **before** pushing (and avoid breaking CI), install pre-commit hooks locally:

```bash
pip install pre-commit
pre-commit install
```

Run checks manually at any time:

```bash
pre-commit run --all-files
```

## 3. Testing Standards

We use **pytest** for unit testing.

### A. Directory Structure

- `tests/`: All test files must reside here.
- `_archive_unused_scripts/`: Archived scripts are **ignored** by tests.

### B. Mocking External Services (LLM)

**CRITICAL**: Do NOT call real LLM APIs in tests.
The CI environment does not have API keys. You MUST mock `safe_call_llm` or `safe_call_llm_async`.

**Example (Correct Way):**

```python
from unittest.mock import patch

@patch('services.reporting_service.safe_call_llm_async')
def test_something(self, mock_llm):
    mock_llm.return_value = "Mocked Response"
    # ... test logic ...
```

## 4. Workflow

1. **Feature Branches**: Develop on `feat/xxx` branches.
1. **Commit Messages**: Clear, descriptive messages.
1. **Pull Requests**: CI must pass (Green Check ✅) before merging to `main`.

______________________________________________________________________

**Lesson Learned**: Fix linting errors immediately. Accumulating them creates "technical debt" that is painful to fix later.
