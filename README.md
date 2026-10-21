# Kathak Practice Guide

A student project for practising a simple alternating-foot drill between lessons, not replacing a teacher. Choose a beat, record yourself in the app, and review rough foot-contact timing. Ask a teacher to approve the exercise and tempo.

## Download the desktop app

Get the Windows or Linux **x64** archive from [GitHub Releases](https://github.com/eknoorsandhu/kathak-guide/releases). Extract the entire archive, then open `KathakGuide.exe` on Windows or run `./KathakGuide` on Linux. Keep the executable and its `_internal` folder together.

Python, FFmpeg/ffprobe, and the pose model are bundled; no Python setup or model download is needed. You still need a webcam and speakers. Linux releases are built on Ubuntu 22.04; older distributions are not supported.

**These builds are unsigned and will likely trigger a security warning**, such as Windows SmartScreen or an antivirus alert. Download only from this project's releases and review the source before deciding whether to run them. Do not disable your security software.

## Run from source

Use Python 3.10–3.13, [uv](https://docs.astral.sh/uv/), FFmpeg (including ffprobe), a webcam and speakers.

```bash
uv sync
uv run python app.py
```

The first analysis downloads a MediaPipe pose model.

## Practice

1. Choose **Beat speed (per minute)**, **Total steps** and your starting foot. At 60 beats per minute, you hear one beat each second; higher numbers are faster. The total duration underneath includes five count-in beats. Left/right means your own feet, not the screen sides.
2. Open the camera. Keep your whole body and feet visible, the camera still, and practise in one spot.
3. Start practice. Recording and five high count-in clicks start together. Wait through the clicks, then alternate one foot contact per beat. The saved audio is the generated track, not the microphone.
4. Recording stops automatically. Review each practice step, use **Replay step** to watch it with the clicks, or open an earlier run from **Saved reviews**.

The review shows just three outcomes:

- **On beat**: the estimated step is close enough to the click.
- **Check timing**: the step looks early or late; the feedback suggests which way to adjust.
- **Couldn't assess**: the camera could not clearly track the expected foot. This does not mean you missed the step.

New reviews use a forgiving allowance of 180 milliseconds before or after each beat, in both the app and command-line analysis. This is a practice setting, not a human-perception threshold or a precise measurement of floor contact. Saved reviews retain the allowance used when they were analyzed.

Exact offsets, timestamps, and extra unmatched movements remain in `results.json` and `drill-review.csv`, rather than cluttering the practice screen.

Runs stay local, with the video, track, drill settings, results and event pictures. Source runs use `runs/` in the project. Desktop builds save under `%LOCALAPPDATA%\KathakGuide\runs` on Windows or `~/.local/share/KathakGuide/runs` on Linux (`$XDG_DATA_HOME/KathakGuide/runs` when set). Keep each run's folder together.

MediaPipe estimates foot positions. A simple lift-and-return rule suggests contacts, but it can miss or mislabel steps. Timing is approximate, no detection doesn't prove a missed step, and this isn't a dance-quality score.

## Code layout

- `app.py`: starts the app.
- `controller.py`: camera, recording, music and navigation.
- `view.py`: Pygame screens and buttons.
- `model.py`: beat track, expected steps and timing review.
- `foot_detection.py`: foot positions and contact candidates.

Practice tones and their fade-outs use [PyDub](https://github.com/jiaaro/pydub) (MIT-licensed). The app schedules five count-in clicks, then alternating left/right cues at the chosen tempo.

## Build a desktop archive

On **64-bit Windows or Linux**, install [uv](https://docs.astral.sh/uv/) and FFmpeg (including ffprobe) on `PATH`, then run:

```bash
uv run --python 3.12 --group build python build.py
```

Build separately on each OS; this does not cross-compile. The script downloads the pose model if needed and produces `dist/KathakGuide-windows-x64.zip` or `dist/KathakGuide-linux-x64.tar.gz`. The extracted folder includes FFmpeg's license and build information in `FFmpeg.txt`; bundled third-party components retain their own licenses.

The **Desktop builds** GitHub Actions workflow builds both platforms. Run it manually to download build artifacts, or push a `v*` tag (for example, `v0.1.0`) to create/update a GitHub Release with both archives attached.

## Separate recordings

Generate the track first and record yourself following it. Keep the WAV beside its JSON and supply the video timestamp of the first count-in click:

```bash
uv run python model.py --output runs/manual-track --bpm 60 --contacts 16
uv run python model.py --video your-video.mp4 --drill runs/manual-track/drill.json --count-in-start 2.35 --output runs/manual-review
```
