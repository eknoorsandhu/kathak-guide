"""beat track + video review bits"""

import argparse
import json
import math
import subprocess
import wave
from pathlib import Path

import cv2
from pydub.generators import Sine

SAMPLE_RATE = 44100
COUNT_IN = 5
STATUS_LABELS = {
    "on_time": "Within timing allowance", "early": "Early candidate",
    "late": "Late candidate", "wrong_foot": "Other-foot candidate",
    "not_detected": "No contact detected", "unmatched": "Unmatched detection",
}


def validate_drill(bpm, contacts, first_foot):
    if not math.isfinite(bpm) or not 30 <= bpm <= 120:
        raise ValueError("Tempo must be between 30 and 120 BPM")
    if type(contacts) is not int or not 4 <= contacts <= 64:
        raise ValueError("Choose 4 to 64 whole contacts")
    if first_foot not in ("left", "right"):
        raise ValueError("Choose the anatomical left or right foot")


def click(frequency, duration):
    milliseconds = duration * 1000
    tone = Sine(frequency, sample_rate=SAMPLE_RATE).to_audio_segment(
        duration=milliseconds, volume=-3)
    return tone.fade_out(milliseconds).raw_data


def create_drill(output, bpm=60, contacts=16, first_foot="left"):
    """make the clicks and save which foot goes with each beat"""
    validate_drill(bpm, contacts, first_foot)
    output = Path(output)
    if (output / "results.json").exists():
        raise ValueError("This folder already contains a completed review")
    output.mkdir(parents=True, exist_ok=True)
    drill = dict(version=1, bpm=bpm, contacts=contacts, first_foot=first_foot,
                 count_in=COUNT_IN, track="practice.wav")
    period = 60 / bpm
    clicks = {"count_in": click(1760, .10), "left": click(550, .06), "right": click(1100, .06)}
    feet = (first_foot, "right" if first_foot == "left" else "left")
    position = 0
    with wave.open(str(output / "practice.wav"), "wb") as track:
        track.setnchannels(1)  # just one audio channel
        track.setsampwidth(2)  # 2 bytes per sample = 16-bit sound
        track.setframerate(SAMPLE_RATE)
        for index in range(COUNT_IN + contacts):
            # start each beat from time zero, rounding one gap at a time slowly drifts
            onset = round(index * period * SAMPLE_RATE)
            if index < COUNT_IN:
                sound = clicks["count_in"]
            else:
                foot = feet[(index - COUNT_IN) % 2]
                sound = clicks[foot]
            track.writeframesraw(bytes((onset - position) * 2))
            track.writeframesraw(sound)
            position = onset + len(sound) // 2
        # Give the last beat its full time too, not just the length of its click.
        track.writeframesraw(bytes((round((COUNT_IN + contacts) * period * SAMPLE_RATE) - position) * 2))
    path = output / "drill.json"
    path.write_text(json.dumps(drill, indent=2) + "\n", encoding="utf-8")
    return path


def load_drill(path):
    path = Path(path)
    drill = json.loads(path.read_text(encoding="utf-8"))
    validate_drill(drill["bpm"], drill["contacts"], drill["first_foot"])
    if drill["version"] != 1 or drill["count_in"] != COUNT_IN or drill["track"] != "practice.wav":
        raise ValueError("Unsupported practice drill")
    frames = round((COUNT_IN + drill["contacts"]) * 60 / drill["bpm"] * SAMPLE_RATE)
    # keep the WAV next to its JSON or this won't load
    with wave.open(str(path.parent / drill["track"]), "rb") as track:
        if (track.getnchannels(), track.getsampwidth(), track.getframerate(), track.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
            raise ValueError("Practice audio must be mono 16-bit PCM at 44100 Hz")
        if track.getnframes() != frames:
            raise ValueError("Practice audio duration does not match this drill")
        track.setpos(frames - 1)
        if len(track.readframes(1)) != 2:
            raise ValueError("Practice audio is truncated")
    return drill


def expected_contacts(drill, count_in_start):
    validate_drill(drill["bpm"], drill["contacts"], drill["first_foot"])
    if not math.isfinite(count_in_start) or count_in_start < 0:
        raise ValueError("The first count-in timestamp must be finite and nonnegative")
    # first count-in click here, NOT the first foot contact
    feet = (drill["first_foot"], "right" if drill["first_foot"] == "left" else "left")
    return [{"beat": index + 1, "foot": feet[index % 2],
             "expected_time": count_in_start + (COUNT_IN + index) * (60 / drill["bpm"])}
            for index in range(drill["contacts"])]


def review_contacts(expected, hits, period, tolerance_ms=80):
    """find contacts near the beats but don't count one hit twice"""
    if not math.isfinite(period) or period <= 0:
        raise ValueError("The beat period must be finite and positive")
    window = .45 * period
    if not math.isfinite(tolerance_ms) or not 0 < tolerance_ms < window * 1000:
        raise ValueError("Timing allowance must be positive and below the assignment window")
    expected, hits = list(expected), list(hits)
    counts = {"expected": len(expected), "detected": len(hits)}
    for status in STATUS_LABELS:
        counts[status] = 0
    events, used = [], set()
    for contact in expected:
        time = contact["expected_time"]
        candidates = []
        for i, hit in enumerate(hits):
            if i not in used and time - window <= hit["time"] <= time + window:
                candidates.append(i)
        event = dict(beat=contact["beat"], expected_foot=contact["foot"], expected_time=time,
                     detected_foot=None, detected_time=None, offset_ms=None,
                     status="not_detected", x=None, y=None)
        if candidates:
            # try the expected foot first, even if the other foot is closer
            correct_foot = []
            for i in candidates:
                if hits[i]["foot"] == contact["foot"]:
                    correct_foot.append(i)
            if correct_foot:
                candidates = correct_foot
            selected = candidates[0]
            for i in candidates:
                if abs(hits[i]["time"] - time) < abs(hits[selected]["time"] - time):
                    selected = i
            used.add(selected)
            hit = hits[selected]
            if hit["foot"] != contact["foot"]:
                status = "wrong_foot"
            elif time - tolerance_ms / 1000 <= hit["time"] <= time + tolerance_ms / 1000:
                status = "on_time"
            else:
                status = "early" if hit["time"] < time else "late"
            event.update(detected_foot=hit["foot"], detected_time=hit["time"],
                         offset_ms=(hit["time"] - time) * 1000, status=status,
                         x=hit.get("x"), y=hit.get("y"))
        counts[event["status"]] += 1
        # nothing detected doesn't mean they missed the step. keep it in the review
        events.append(event)
    # Don't quietly throw away the leftover detections either.
    for index in sorted(set(range(len(hits))) - used, key=lambda i: hits[i]["time"]):
        hit = hits[index]
        events.append(dict(beat=None, expected_foot=None, expected_time=None,
                           detected_foot=hit["foot"], detected_time=hit["time"], offset_ms=None,
                           status="unmatched", x=hit.get("x"), y=hit.get("y")))
        counts["unmatched"] += 1
    return {"counts": counts, "events": events}


def video_info(video):
    """need the video length here. audio can carry on after the picture stops"""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    opened = cap.isOpened()
    cap.release()
    if not opened or not math.isfinite(fps) or fps <= 0:
        raise ValueError("The recording needs a readable video stream and frame rate")
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries"]
    probe = subprocess.run(command + ["stream=duration", "-of", "json", str(video)],
                           check=True, capture_output=True, text=True)
    streams = json.loads(probe.stdout)["streams"]
    if not streams:
        raise ValueError("No video stream found")
    duration = streams[0].get("duration")
    if duration is None or duration == "N/A":
        probe = subprocess.run(command + ["packet=pts_time,duration_time", "-of", "json", str(video)],
                               check=True, capture_output=True, text=True)
        intervals = [(float(p["pts_time"]), float(p["pts_time"]) + float(p.get("duration_time", 1 / fps)))
                     for p in json.loads(probe.stdout)["packets"] if "pts_time" in p]
        if not intervals:
            raise ValueError("Could not determine recorded video coverage")
        duration = max(end for _, end in intervals) - min(start for start, _ in intervals)
    duration = float(duration)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("The video duration must be finite and positive")
    return fps, duration


def analyze_recording(video, drill_path, count_in_start, output, tolerance_ms=80, progress=None):
    """check the clip against the saved drill and write out what we found"""
    output, video, drill_path = Path(output), Path(video).resolve(), Path(drill_path).resolve()
    if (output / "results.json").exists():
        raise ValueError("This folder already contains a completed review")
    drill = load_drill(drill_path)
    expected = expected_contacts(drill, count_in_start)
    period = 60 / drill["bpm"]
    review_contacts(expected, [], period, tolerance_ms)
    fps, duration = video_info(video)
    track_end = count_in_start + (COUNT_IN + drill["contacts"]) * period
    if track_end > duration + 1 / fps:  # Allow a frame for rounded video timestamps.
        raise ValueError("Record the complete count-in and exercise; unrecorded contacts cannot be reviewed")
    # Pose stuff is slow to import, so check the recording first.
    from foot_detection import find_hits, get_feet
    def update(percent, text):
        if progress:
            progress(percent, text)
    update(5, "Reading the prescribed contact schedule")
    # grab some of the count-in too, for a starting foot height
    start = max(count_in_start, expected[0]["expected_time"] - .45 * period - .8)
    feet = get_feet(video, start, track_end - start, progress=update, pose_fps=15)
    # The camera might not be exactly 30 fps. Use the rate we actually sampled at.
    sample_fps = fps / max(1, round(fps / 15))
    hits = find_hits(feet, .006)
    hits = [hit for hit in hits if expected[0]["expected_time"] - .45 * period <= hit["time"]
            <= expected[-1]["expected_time"] + .45 * period]
    update(88, "Assigning candidates to expected contacts")
    result = review_contacts(expected, hits, period, tolerance_ms)
    update(92, "Saving review results")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "drill": drill, "drill_path": str(drill_path), "video": str(video),
        "count_in_start": count_in_start, "tolerance_ms": tolerance_ms,
        "matching_window_ms": .45 * period * 1000, "video_fps": fps,
        "pose_sample_fps": sample_fps, "min_lift": .006,
    }
    report.update(result)
    with (output / "results.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    update(100, "Review ready")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--bpm", type=float, default=60)
    parser.add_argument("--contacts", type=int, default=16)
    parser.add_argument("--first-foot", choices=("left", "right"), default="left")
    parser.add_argument("--video")
    parser.add_argument("--drill")
    parser.add_argument("--count-in-start", type=float)
    parser.add_argument("--tolerance-ms", type=float, default=80)
    args = parser.parse_args()
    try:
        if args.video:
            if args.drill is None or args.count_in_start is None:
                parser.error("--video requires --drill and --count-in-start")
            analyze_recording(args.video, args.drill, args.count_in_start, args.output, args.tolerance_ms)
            print(f"Review saved: {Path(args.output) / 'results.json'}")
        else:
            print(f"Drill saved: {create_drill(args.output, args.bpm, args.contacts, args.first_foot)}")
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Cannot complete practice: {error}\n")


if __name__ == "__main__":
    main()
