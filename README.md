# Kathak Practice Guide

A student project for practising a simple alternating-foot drill between lessons, not replacing a teacher. Ask a teacher to approve the exercise and tempo.

Use Python 3.10–3.13:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python model.py --output runs/practice-track --bpm 60 --contacts 16 --first-foot left
```

On Windows, activate the environment with `.venv\Scripts\activate.bat` in Command Prompt or `.venv\Scripts\Activate.ps1` in PowerShell instead of the `source` command.

The app currently shows the exercise guide. The generator saves `practice.wav` and `drill.json`; keep them together.

Wait through the five high count-in clicks, then alternate one foot contact per beat. Choose 30–120 BPM and 4–64 contacts. Left and right use different pitches and mean your own feet, not the screen sides.

Record yourself following the track with your whole body and feet visible. Contact analysis comes next.

Practice tones use [PyDub](https://github.com/jiaaro/pydub) (MIT-licensed). The app schedules five count-in clicks, then alternating left/right cues at the chosen tempo.
