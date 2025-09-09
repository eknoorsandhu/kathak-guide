# Kathak Practice Guide

A student project for practising a simple alternating-foot drill between lessons, not replacing a teacher.

Use Python 3.10–3.13:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

On Windows, activate the environment with `.venv\Scripts\activate.bat` in Command Prompt or `.venv\Scripts\Activate.ps1` in PowerShell instead of the `source` command.

For now, the Pygame window explains camera placement and the exercise. The plan is to generate our own beat track, record the student following it, and give rough timing feedback. Ask a teacher to approve the exercise and tempo.
