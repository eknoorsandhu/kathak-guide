"""Build a portable folder on Windows or Linux; FFmpeg must be on PATH."""
import platform
import shutil
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from foot_detection import get_model

ROOT = Path(__file__).resolve().parent


def main():
    if sys.platform not in ("win32", "linux") or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Build on 64-bit Windows or Linux.")
    tools = [shutil.which(name) for name in ("ffmpeg", "ffprobe")]
    if not all(tools):
        raise SystemExit("Install FFmpeg (including ffprobe) before building.")

    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "KathakGuide", "--collect-all", "mediapipe",
        "--add-data", f"{get_model().parent}:.models",
    ]
    for tool in tools:
        command += ["--add-binary", f"{tool}:ffmpeg"]
    command.append(str(ROOT / "app.py"))
    subprocess.run(command, cwd=ROOT, check=True)

    folder = ROOT / "dist" / "KathakGuide"
    for name in ("README.md", "LICENSE"):
        shutil.copy2(ROOT / name, folder / name)
    for package in distributions():
        for file in package.files or ():
            if file.name.lower().startswith(("license", "copying", "notice")) or file.name == "METADATA":
                source = Path(package.locate_file(file))
                if source.is_file():
                    target = folder / "licenses" / package.metadata["Name"] / file
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    # Preserve FFmpeg's license and exact build configuration alongside the binaries.
    notice = folder / "FFmpeg.txt"
    with notice.open("w", encoding="utf-8") as output:
        output.write("FFmpeg: https://ffmpeg.org\nSource: https://ffmpeg.org/download.html\n\n")
        for option in ("-version", "-L"):
            result = subprocess.run([tools[0], option], check=True, capture_output=True, text=True)
            output.write(result.stdout + result.stderr + "\n")

    target = "windows" if sys.platform == "win32" else "linux"
    archive = shutil.make_archive(
        str(ROOT / "dist" / f"KathakGuide-{target}-x64"),
        "zip" if target == "windows" else "gztar",
        root_dir=ROOT / "dist", base_dir="KathakGuide",
    )
    print(f"Built {archive}")


if __name__ == "__main__":
    main()
