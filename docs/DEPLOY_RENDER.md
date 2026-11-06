# Deploy Inventory Solver to Render (GitHub → public URL)

This repository runs **NiceGUI**, not Streamlit. The server entry point is
`main.py`; do **not** rename it to `app.py` or use Streamlit Cloud.

## Before publishing

1. On your Windows workstation run `uv lock` with Python 3.12 available.
2. Verify `uv run --active python -m pytest -q` (when using your activated
   environment) and `uv run --active python main.py` locally.
3. Commit `uv.lock` along with `main.py`, `inventory_solver/`, `pyproject.toml`,
   `render.yaml`, `examples/`, and the application docs/tests.
4. Do not commit `.venv`, caches, authentication tokens, uploaded Excel files
   containing private data, scanned handwritten solutions, or copyrighted
   textbook PDFs. The bundled Excel template is appropriate for this repo.

## Render Blueprint route (recommended)

1. Push the repository to GitHub.
2. Visit https://dashboard.render.com and sign in with GitHub.
3. Choose **New → Blueprint**, select your GitHub repository, and authorize
   the connection if requested.
4. Render reads the included `render.yaml`:
   - Python web service on the Free plan
   - Build: `pip install uv && uv sync --no-dev`
   - Start: `uv run --no-dev python main.py`
   - Python: `UV_PYTHON=3.12`
   - `APP_ENV=production`
5. Review the service settings, apply/deploy, and inspect the build and runtime
   logs. Render assigns a real `*.onrender.com` URL only after the service is
   created; it is not predetermined.
6. Open the URL and test **HW1, HW3, HW2, HW4, HW6, HW5**, long LaTeX steps,
   Excel import, and solution export from the deployed version.

## Alternative: Web Service route

If the Blueprint option is unavailable, choose **New → Web Service**, connect
GitHub, choose the Free instance, and use the same build/start commands above.
Set environment variables `APP_ENV=production` and `UV_PYTHON=3.12`. Let Render
supply the `PORT`; `main.py` already reads it and binds to `0.0.0.0`.

## Free-plan caveats

Render Free web services spin down after approximately 15 minutes without
traffic. The next visitor can see a startup delay. Files changed during a
session do not persist through a spin-down or redeployment. Uploaded Excel
inputs are intended to be processed temporarily in memory; the application
is not a persistent database. Compute and memory are limited, especially for
large HW4 integer optimizations. Review account-specific quotas and current
terms before using the deployment for many concurrent visitors.

Do not use GitHub Pages as the host: this project requires a running Python
server (including NiceGUI's WebSocket connection).

Official documentation:
- https://render.com/docs/your-first-deploy
- https://render.com/docs/free
