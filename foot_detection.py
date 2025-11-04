"""trying to spot foot lifts/landings, not measuring actual floor contact"""

import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
MODEL_PATH = Path(__file__).parent / ".models" / "pose_landmarker_full.task"


def get_model():
    """download the pose model if we don't have it yet"""
    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(exist_ok=True)
        print("Downloading pose model...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


def get_feet(video, start, duration, progress=None, pose_fps=15):
    """sample the video and save where the feet are"""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    # roughly 15 frames/sec, doing every frame would take ages
    stride = max(1, round(fps / pose_fps))
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(get_model())),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
    )
    feet, frame_number, last_ms, last_progress = [], 0, -1, -1
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if time > start + duration:
                break
            if progress:
                percent = 15 + int(70 * min(1, (time - start) / duration))
                if percent > last_progress:
                    progress(percent, "Tracking feet")
                    last_progress = percent
            if frame_number % stride == 0:
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                # times need to keep increasing or MediaPipe complains
                timestamp = max(round(time * 1000), last_ms + 1)
                result = detector.detect_for_video(image, timestamp)
                last_ms = timestamp
                if result.pose_landmarks:
                    points = result.pose_landmarks[0]
                    for foot, indexes in (("left", (27, 29, 31)), ("right", (28, 30, 32))):
                        foot_points = [points[i] for i in indexes]
                        lowest = max(foot_points, key=lambda point: point.y)
                        feet.append({
                            "time": float(time), "foot": foot, "x": float(lowest.x),
                            "y": float(lowest.y),
                            "visible": float(min(point.visibility for point in foot_points)),
                        })
            frame_number += 1
    cap.release()
    return feet


def find_hits(feet, min_lift=0.006):
    """wait for a foot to go up, then come back near where it started"""
    hits = []
    for foot in ("left", "right"):
        samples = [row for row in feet if row["foot"] == foot]
        if len(samples) < 5:
            continue
        # Average every 3 frames to make the data smoother
        y_values = [row["y"] for row in samples]
        y = []

        for i in range(len(y_values) - 2):
            average = (y_values[i] + y_values[i + 1] + y_values[i + 2]) / 3
            y.append(average)

        y = np.array(y)
        ground = y[0]  # just a remembered low position, not actual floor tracking
        raised = False
        last_time = -999.0
        for i, height in enumerate(y):
            row = samples[i + 1]  # middle frame of this average
            if row["visible"] < .6:
                ground = height
                raised = False
                continue
            if not raised:
                ground = max(ground, height)
                raised = ground - height >= min_lift
            elif height >= ground - min_lift / 2 and row["time"] - last_time >= .18:
                hits.append(row)
                # need a new lift before we count another return
                raised, ground = False, height
                last_time = row["time"]
    return sorted(hits, key=lambda row: row["time"])
