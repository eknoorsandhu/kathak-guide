"""camera, music and keeping the app moving"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
import pygame

import model
from view import View

ROOT = Path(__file__).parent
if getattr(sys, "frozen", False):
    data_home = (Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
                 if sys.platform == "win32"
                 else Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"))
    ROOT = data_home / "KathakGuide"
FPS = 30


class Recording:
    """save frames for now, add our audio once recording is done"""

    def __init__(self, folder, frame):
        self.folder = Path(folder)
        self.frames = 0
        self.previous = frame
        height, width = frame.shape[:2]
        self.raw = self.folder / "raw.avi"
        # OpenCV needs a code for the video format. MJPG works for this temporary AVI
        video_format = cv2.VideoWriter.fourcc("M", "J", "P", "G")
        self.writer = cv2.VideoWriter(str(self.raw), video_format, FPS, (width, height))
        if not self.writer.isOpened():
            raise OSError("Could not create the camera recording")

    def write(self, frame, elapsed):
        slot = int(elapsed * FPS)
        # camera might stall for a bit. hold the last frame so video timing doesn't shrink
        while self.frames < slot:
            self.writer.write(self.previous)
            self.frames += 1
        if self.frames == slot:
            self.writer.write(frame)
            self.frames += 1
        self.previous = frame

    def finish(self, count_in_start):
        self.writer.release()
        video = self.folder / "recording.mp4"
        audio_path = self.folder / "recording_audio.wav"
        with wave.open(str(self.folder / "practice.wav"), "rb") as song:
            with wave.open(str(audio_path), "wb") as audio:
                audio.setparams(song.getparams())
                rate = song.getframerate()
                # the camera starts first, so put that quiet bit before the music
                # our WAV is mono and each sample takes 2 bytes
                audio.writeframes(bytes(round(count_in_start * rate) * 2))
                audio.writeframes(song.readframes(song.getnframes()))
                # keep the sound file going until the video ends
                video_seconds = self.frames / FPS
                extra_samples = round(video_seconds * rate) - audio.getnframes()
                if extra_samples > 0:
                    audio.writeframes(bytes(extra_samples * 2))

        # ffmpeg just joins the picture and sound now
        # H.264 + yuv420p makes an MP4 that ordinary video players can open
        subprocess.run([
            "ffmpeg", "-nostdin", "-y", "-i", str(self.raw), "-i", str(audio_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(video),
        ], check=True, capture_output=True)
        self.raw.unlink()
        audio_path.unlink()
        return video


class App:
    def __init__(self, camera=0, run_root=None):
        self.view = View()
        self.run_root = Path(run_root or ROOT / "runs")
        self.camera_index = camera if isinstance(camera, int) else 0
        self.source = camera
        self.page = "home"
        self.message = ""
        self.progress = ""
        self.bpm = 60
        self.contacts = 16
        self.first_foot = "left"
        # same frame variable for the live camera and the review picture
        self.frame = self.capture = self.recording = self.report = self.drill = None
        self.run_dir = self.count_in_start = None
        self.elapsed = self.event_index = self.history_index = 0
        self.history = []
        self.review_steps = []
        self.updates = queue.Queue()
        self.running = True
        self.worker = None

    def handle(self, action):
        if action in ("bpm_down", "bpm_up"):
            self.bpm = min(120, max(30, self.bpm + (-5 if action == "bpm_down" else 5)))
        elif action in ("contacts_down", "contacts_up"):
            self.contacts = min(64, max(4, self.contacts + (-4 if action == "contacts_down" else 4)))
        elif action == "foot":
            self.first_foot = "right" if self.first_foot == "left" else "left"
        elif action in ("camera_down", "camera_up"):
            self.camera_index = max(0, self.camera_index + (-1 if action == "camera_down" else 1))
            self.source = self.camera_index
        elif action == "preview" and self.page == "home":
            self.capture = cv2.VideoCapture(self.source)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.capture.isOpened():
                raise OSError("Camera unavailable. Check its index, permissions, or other camera apps.")
            self.page, self.message = "preview", ""
            if isinstance(self.source, str):
                self.message = "Using a video file as the camera source (engineering check, not live capture)."
        elif action == "record" and self.page == "preview":
            if self.frame is None:
                raise OSError("Wait for the camera preview before recording")
            if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
                raise OSError("Install ffmpeg and ffprobe before recording")
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=256)
            # The short random bit avoids overwriting two runs started in the same second.
            self.run_dir = self.run_root / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"
            path = model.create_drill(self.run_dir, self.bpm, self.contacts, self.first_foot)
            self.drill = model.load_drill(path)
            pygame.mixer.music.load(str(self.run_dir / "practice.wav"))
            self.recording = Recording(self.run_dir, self.frame)
            self.started, self.elapsed = time.monotonic(), 0
            pygame.mixer.music.play()
            self.count_in_start = time.monotonic() - self.started
            self.recording.write(self.frame, 0)
            self.page = "recording"
        elif action == "cancel" and self.page == "recording":
            folder = self.recording.folder
            self.close_devices()
            # only delete this attempt! old reviews should stay
            shutil.rmtree(folder)
            self.page, self.message = "home", "Recording cancelled; no feedback was saved."
        elif action == "history":
            self.history = []
            for path in sorted(self.run_root.glob("*/results.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    if "counts" in json.loads(path.read_text()):
                        self.history.append(path.parent)
                except (OSError, ValueError):
                    continue
            self.page, self.history_index = "history", 0
        elif action in ("history_prev", "history_next") and self.history:
            self.history_index = (self.history_index + (-1 if action == "history_prev" else 1)) % len(self.history)
        elif action == "history_open" and self.history:
            self.run_dir = self.history[self.history_index]
            self.open_review(json.loads((self.run_dir / "results.json").read_text()))
        elif action in ("event_prev", "event_next"):
            self.event_index = (self.event_index + (-1 if action == "event_prev" else 1)) % len(self.review_steps)
            self.show_event()
        elif action == "watch":
            self.start_watch()
        elif action == "back":
            was_watching = self.page == "watch"
            self.close_devices()
            if was_watching:
                self.show_event()
            else:
                self.page, self.message = "home", ""

    def close_devices(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        if self.recording is not None:
            self.recording.writer.release()
            self.recording = None
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.stop()

    def open_review(self, report):
        self.report = report
        # Extra movements stay in the export, not in the step-by-step practice review.
        self.review_steps = [event for event in report["events"] if event["beat"] is not None]
        self.event_index = 0
        self.show_event()

    def show_event(self):
        event = self.review_steps[self.event_index] if self.review_steps else None
        self.frame = cv2.imread(str(self.run_dir / event["image"])) if event and event.get("image") else None
        self.page = "results"

    def start_watch(self):
        event = self.review_steps[self.event_index]
        self.capture = cv2.VideoCapture(self.report["video"])
        if not self.capture.isOpened():
            raise OSError("Saved source video is missing or unreadable")
        self.watch_from = event["watch_start"]
        self.watch_fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, int(self.watch_from * self.watch_fps))
        self.watch_length = event["watch_end"] - event["watch_start"]
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=256)
        with wave.open(str(Path(self.report["drill_path"]).parent / "practice.wav"), "rb") as track:
            # Start the audio partway through too, since this is only a short replay.
            offset = max(0, event["watch_start"] - self.report["count_in_start"])
            track.setpos(min(track.getnframes(), round(offset * 44100)))
            self.watch_sound = pygame.mixer.Sound(buffer=track.readframes(round(self.watch_length * 44100)))
        self.watch_sound.play()
        self.watch_started, self.page = time.monotonic(), "watch"

    def finish_recording(self):
        recording, start = self.recording, self.count_in_start
        self.close_devices()
        self.page, self.progress = "processing", "Saving video and beat track..."
        # do the slow part off to the side so the window doesn't freeze
        def update_progress(percent, text):
            self.updates.put(("progress", f"{percent}% {text}"))

        def work():
            try:
                video = recording.finish(start)
                report = model.analyze_recording(video, recording.folder / "drill.json", start,
                                                recording.folder, progress=update_progress)
                self.updates.put(("result", report))
            except Exception as error:
                self.updates.put(("error", f"{error}. Recording files are in {recording.folder}"))
        # closing the window shouldn't stop a half-saved review
        self.worker = threading.Thread(target=work)
        self.worker.start()

    def tick(self):
        if self.page == "watch":
            elapsed = time.monotonic() - self.watch_started
            if elapsed >= self.watch_length:
                self.handle("back")
                return
            target = int((self.watch_from + elapsed) * self.watch_fps)
            # Catch up to the clock if drawing was slow, instead of letting replay drift.
            while self.capture.get(cv2.CAP_PROP_POS_FRAMES) <= target:
                if not self.capture.grab():
                    self.handle("back")
                    return
            ok, self.frame = self.capture.retrieve()
            if not ok:
                raise OSError("Could not decode the saved replay")
        elif self.page in ("preview", "recording"):
            ok, self.frame = self.capture.read()
            if not ok:
                raise OSError("Camera feed stopped; this attempt cannot be reviewed")
        if self.page == "recording":
            self.elapsed = time.monotonic() - self.started
            self.recording.write(self.frame, self.elapsed)
            duration = (model.COUNT_IN + self.contacts) * 60 / self.bpm
            if self.elapsed >= self.count_in_start + duration:
                self.finish_recording()
        # The worker puts messages here; only this loop changes what's on screen.
        while not self.updates.empty():
            kind, value = self.updates.get()
            if kind == "result":
                self.open_review(value)
            elif kind == "error":
                self.page, self.message = "home", value
            else:
                self.progress = value

    def run(self):
        clock = pygame.time.Clock()
        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    action = self.view.action(event)
                    if action:
                        try:
                            self.handle(action)
                        except Exception as error:
                            self.close_devices()
                            self.page, self.message = "home", str(error)
                try:
                    self.tick()
                except Exception as error:
                    self.close_devices()
                    self.page, self.message = "home", str(error)
                self.view.draw(self)
                pygame.display.flip()
                clock.tick(FPS)
        finally:
            self.close_devices()
            pygame.quit()
