"""beat track + saved drill settings"""

import argparse
import json
import math
import wave
from pathlib import Path

from pydub.generators import Sine


SAMPLE_RATE = 44100
COUNT_IN = 5


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
    return tone.raw_data


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an alternating-foot practice track")
    parser.add_argument("--output", required=True)
    parser.add_argument("--bpm", type=float, default=60)
    parser.add_argument("--contacts", type=int, default=16)
    parser.add_argument("--first-foot", choices=("left", "right"), default="left")
    args = parser.parse_args()
    print(f"Drill saved: {create_drill(args.output, args.bpm, args.contacts, args.first_foot)}")
