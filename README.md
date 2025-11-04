# Kathak Practice Guide

A student project for practising a simple alternating-foot drill between lessons, not replacing a teacher. Ask a teacher to approve the exercise and tempo.

Use Python 3.10–3.13 and FFmpeg (including ffprobe). The first analysis downloads a MediaPipe pose model.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python model.py --output runs/practice-track --bpm 60 --contacts 16 --first-foot left
```

On Windows, activate the environment with `.venv\Scripts\activate.bat` in Command Prompt or `.venv\Scripts\Activate.ps1` in PowerShell instead of the `source` command.

The app shows the guide; recording is still separate. Wait through five count-in clicks, then alternate one foot contact per beat. Keep your whole body and feet visible, the camera still, and practise in one spot. Left/right means your own feet.

To review a recording, give the timestamp of its first count-in click:

```bash
python model.py --video your-video.mp4 --drill runs/practice-track/drill.json --count-in-start 2.35 --output runs/practice-review
```

Keep the generated WAV beside its JSON. The review saves its results in `results.json`. It prefers the expected foot, then the closest unused candidate.

MediaPipe estimates foot positions. A simple lift-and-return rule suggests contacts, but hidden feet and small lifts can be missed. Timing is approximate; no detection doesn't prove a missed step, and this isn't a dance-quality score.

Practice tones and their fade-outs use [PyDub](https://github.com/jiaaro/pydub) (MIT-licensed). The app schedules five count-in clicks, then alternating left/right cues at the chosen tempo.
