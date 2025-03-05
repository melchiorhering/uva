# Application Documentation

This document describes how to set up and run the application using `uv` as the package manager and `streamlit`.

## Prerequisites

- Python 3.8 or higher
- `uv` package manager

## Setup Instructions

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create and activate a virtual environment

```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# OR
.venv\Scripts\activate  # On Windows
```

### 3. Install (sync) dependencies with `pyproject.toml`

Syncing with `pyproject.toml` will install all dependencies listed in the file.

```bash
uv sync
```

Lock + upgrade will update all dependencies to the latest versions.

```bash
uv lock --upgrade
```

Adding a new dependency:

```bash
uv add <package_name>
```

## Running the Application

Navigate to the project directory and run:

```bash
cd app/
streamlit run app.py
```

The application should now be running and accessible at http://localhost:8501.

## Troubleshooting

- If you encounter permission issues with uv, try running the commands with sudo (on Unix/macOS).
- For port conflicts, you can specify a different port: `streamlit run app.py --server.port 8502`
- To enable debugging: `streamlit run app.py --logger.level=debug`
