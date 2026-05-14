# uv-lock-check

A GitHub Action that validates if your `uv.lock` file and optionally
`requirements.txt` files are in sync with your `pyproject.toml` file.

## Features

- Validates `uv.lock` file against `pyproject.toml`
- Optionally validates `requirements.txt` files
- Supports custom paths for all files
- Supports custom uv commands for requirements generation
- Automatically detects Python version from `pyproject.toml`

## Usage

### Basic Usage

```yaml
name: Check Dependencies

on:
  pull_request:
    paths:
      - 'pyproject.toml'
      - 'uv.lock'
      - 'requirements.txt'

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hbelmiro/uv-lock-check@v1
```

### With Custom Paths

```yaml
- uses: hbelmiro/uv-lock-check@v1
  with:
    pyproject-path: 'path/to/pyproject.toml'
    requirements-path: 'path/to/requirements.txt'
```

### With Custom Command

```yaml
- uses: hbelmiro/uv-lock-check@v1
  with:
    command: 'uv pip compile --python-platform=linux pyproject.toml -o requirements-linux.txt'
    requirements-path: 'requirements-linux.txt'
```

## Inputs

| Input               | Description                                                                                                         | Required | Default          |
|---------------------|---------------------------------------------------------------------------------------------------------------------|----------|------------------|
| `pyproject-path`    | Path to the pyproject.toml file                                                                                     | No       | `pyproject.toml` |
| `requirements-path` | Path to the requirements.txt file. If empty, will look for requirements.txt in the same directory as pyproject.toml | No       | `''`             |
| `command`           | uv command to run for validation                                                                                    | No       | `uv sync`        |
| `show-diff`         | Show git diff output when files are out of sync                                                                     | No       | `false`          |
| `diff-max-lines`    | Maximum number of diff lines to display when `show-diff` is enabled                                                 | No       | `200`            |

## How It Works

1. The action reads the Python version from your `pyproject.toml` file
2. It runs the specified command (defaults to `uv sync`) to check
   if the `uv.lock` file is in sync
3. If a `requirements.txt` file is specified:
   - It generates a new requirements file using the provided command
   - Compares it with the existing one
   - Fails if they don't match

## Examples

### Platform-Specific Requirements

```yaml
- uses: hbelmiro/uv-lock-check@v1
  with:
    command: 'uv pip compile --python-platform=linux pyproject.toml -o requirements-linux.txt'
    requirements-path: 'requirements-linux.txt'
```

### With Diff Output on Failure

```yaml
- uses: hbelmiro/uv-lock-check@v1
  with:
    show-diff: 'true'
    diff-max-lines: '500'
```

### Multiple Requirements Files

```yaml
- name: Check Linux Requirements
  uses: hbelmiro/uv-lock-check@v1
  with:
    command: 'uv pip compile --python-platform=linux pyproject.toml -o requirements-linux.txt'
    requirements-path: 'requirements-linux.txt'

- name: Check Windows Requirements
  uses: hbelmiro/uv-lock-check@v1
  with:
    command: 'uv pip compile --python-platform=windows pyproject.toml -o requirements-win.txt'
    requirements-path: 'requirements-win.txt'
```

## Development

### Setup

```bash
uv sync --group dev
```

### Testing

Run unit tests:

```bash
uv run pytest -v
```

Run with coverage:

```bash
uv run pytest --cov --cov-report=term-missing
```

### Linting and type checking

```bash
uv run ruff check .
uv run ty check
```

### Pre-commit hooks

```bash
uv run pre-commit run --all-files
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details
