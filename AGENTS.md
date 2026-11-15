# Architecture

- main.py owns AstrBot registration, administrator checks and multimodal tool results.
- phone_use/client.py owns only protocol v1 transport. Keep device operations in the Android repository.
- Do not add remote network control, automatic action retries, auto-granted permissions or persisted session IDs.
- Read the socket name from ASTRBOT_PHONE_USE_SOCKET; do not write installation-specific files into the plugin directory.
- Never log screenshot contents, input text, credentials or full operation payloads.
- Keep metadata.yaml and pyproject.toml versions aligned. Use AstrBot's standard plugin installation lifecycle.

# Verification

Run python -m unittest discover -s tests -v with Python 3.10+, ruff check ., and ruff format --check .
Before committing, run gitleaks dir . --config .gitleaks.toml --no-banner --redact=100. Install hooks with git config core.hooksPath .githooks. Do not commit credentials or device captures.
