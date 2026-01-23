# Kathak Practice Guide

A student project for practising a simple alternating-foot drill between lessons, not replacing a teacher. Choose a beat, record yourself in the app, and review rough foot-contact timing. Ask a teacher to approve the exercise and tempo.

## Run

Use Python 3.10–3.13, FFmpeg (including ffprobe), a webcam and speakers.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

On Windows, activate the environment with `.venv\Scripts\activate.bat` in Command Prompt or `.venv\Scripts\Activate.ps1` in PowerShell instead of the `source` command.

The first analysis downloads a MediaPipe pose model.

## Practice

1. Choose **Tempo (BPM)**, **Total steps** and your starting foot. The total duration underneath is stepping time plus five count-in beats. Left/right means your own feet, not the screen sides.
2. Open the camera. Keep your whole body and feet visible, the camera still, and practise in one spot.
3. Start practice. Recording and five high count-in clicks start together. Wait through the clicks, then alternate one foot contact per beat. The saved audio is the generated track, not the microphone.
4. Recording stops automatically. Browse the feedback, replay a moment, or open an earlier run from **Saved reviews**.

Runs stay local in `runs/`, with the video, track, drill settings, results and event pictures. Keep each run's folder together.

MediaPipe estimates foot positions. A simple lift-and-return rule suggests contacts, but it can miss or mislabel steps. Timing is approximate, no detection doesn't prove a missed step, and this isn't a dance-quality score.

## Code layout

- `app.py`: starts the app.
- `controller.py`: camera, recording, music and navigation.
- `view.py`: Pygame screens and buttons.
- `model.py`: beat track, expected steps and timing review.
- `foot_detection.py`: foot positions and contact candidates.

Practice tones and their fade-outs use [PyDub](https://github.com/jiaaro/pydub) (MIT-licensed). The app schedules five count-in clicks, then alternating left/right cues at the chosen tempo.

## Separate recordings

Generate the track first and record yourself following it. Keep the WAV beside its JSON and supply the video timestamp of the first count-in click:

```bash
python model.py --output runs/manual-track --bpm 60 --contacts 16
python model.py --video your-video.mp4 --drill runs/manual-track/drill.json --count-in-start 2.35 --output runs/manual-review
```
