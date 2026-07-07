"""
main.py — Entry point
=====================
AI Smart Car Access System  (Class 10 AI School Project)

Run:
    python main.py            → full AI mode (needs DeepFace installed)
    python main.py --demo     → demo mode (UI works without the AI model)
    python main.py --camera 1 → use a different webcam

DISCLAIMER: Educational prototype only. AI age estimation is
approximate and NOT legally accurate.
"""

import argparse
import sys
import tkinter as tk

from camera import FaceCamera
from age_detector import AgeDetector
from ui import DashboardApp


def parse_arguments():
    """Read command-line options."""
    parser = argparse.ArgumentParser(
        description="AI Smart Car Access System — educational prototype."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run without the AI model (simulated ages) — good for rehearsal.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam index (default 0 = built-in laptop camera).",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Build the three main components (object-oriented design):
    camera = FaceCamera(camera_index=args.camera)      # the "in-car camera"
    detector = AgeDetector(demo_mode=args.demo)        # the AI brain
    root = tk.Tk()                                     # the "infotainment display"

    app = DashboardApp(root, camera, detector, demo_mode=args.demo)

    # Make sure the webcam is released even if the window is closed early.
    def on_close():
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
