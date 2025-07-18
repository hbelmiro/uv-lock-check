# uv-lock-check

A GitHub Action that validates if your `uv.lock` file and optionally `requirements.txt` files are in sync with your `pyproject.toml` file.

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

## How It Works

1. The action reads the Python version from your `pyproject.toml` file
2. It runs the specified command (defaults to `uv sync`) to check if the `uv.lock` file is in sync
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

### Testing

The action includes a test workflow that verifies different scenarios:

- Basic usage (just uv.lock)
- With requirements.txt
- With custom requirements command
- Failure cases

To run the tests locally:

1. Create a test project:
```bash
mkdir test-project
cd test-project
```

2. Create a pyproject.toml:
```toml
[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.31.0",
    "pytest>=7.4.0",
]
```

3. Generate the lock file:
```bash
uv sync
```

4. Run the action:
```bash
# From the action's root directory
./verify.sh
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details 