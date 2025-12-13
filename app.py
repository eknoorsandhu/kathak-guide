"""opens the practice app"""
import argparse

from controller import App

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", default="0", help="Camera index; a video path is also accepted for engineering checks")
    args = parser.parse_args()
    # a number uses the webcam, a filename lets us try an existing clip
    camera = int(args.camera) if args.camera.isdigit() else args.camera
    App(camera).run()
