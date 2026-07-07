"""
camera.py — Webcam + Face Detection module
==========================================
Part of: AI Smart Car Access System (Class 10 AI Project)

This module wraps the laptop webcam (acting as the "in-car camera")
and performs real-time face detection using OpenCV's built-in
Haar Cascade classifier (no extra model download needed — it ships
with the opencv-python package).

Classes:
    FaceCamera — opens the webcam, reads frames, finds faces.
"""

import cv2


class FaceCamera:
    """Manages the webcam and continuous face detection."""

    def __init__(self, camera_index=0, width=960, height=540):
        """
        Args:
            camera_index: which camera to use (0 = default laptop webcam).
            width/height: preferred capture resolution.
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.capture = None

        # Haar Cascade face detector — bundled with OpenCV, loads instantly.
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    # ------------------------------------------------------------------ #
    #  Camera control
    # ------------------------------------------------------------------ #
    def open(self):
        """Open the webcam. Returns True on success, False otherwise."""
        self.capture = cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            return False

        # Ask the camera for our preferred resolution (it may pick the closest).
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return True

    def is_open(self):
        """True if the webcam is currently open and usable."""
        return self.capture is not None and self.capture.isOpened()

    def release(self):
        """Release the webcam so other apps can use it."""
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    # ------------------------------------------------------------------ #
    #  Frame reading + face detection
    # ------------------------------------------------------------------ #
    def read(self):
        """
        Grab one frame and detect faces in it.

        Returns:
            (ok, frame, faces)
            ok    — True if a frame was captured.
            frame — the BGR image (mirrored, like a selfie camera).
            faces — list of (x, y, w, h) rectangles, one per detected face.
        """
        if not self.is_open():
            return False, None, []

        ok, frame = self.capture.read()
        if not ok or frame is None:
            return False, None, []

        # Mirror the image so it behaves like a mirror (more natural for the user).
        frame = cv2.flip(frame, 1)

        faces = self._detect_faces(frame)
        return True, frame, faces

    def _detect_faces(self, frame):
        """
        Detect faces on a downscaled grayscale copy (much faster),
        then scale the rectangles back up to full-frame coordinates.
        """
        # Work at half size for speed — Haar cascades are CPU-heavy.
        scale = 0.5
        small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # improves detection in poor lighting

        detections = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,   # how much the image is shrunk at each scan level
            minNeighbors=6,    # higher = fewer false positives
            minSize=(48, 48),  # ignore tiny "faces" (usually noise)
        )

        # Scale rectangles back to the original frame size.
        inv = 1.0 / scale
        return [
            (int(x * inv), int(y * inv), int(w * inv), int(h * inv))
            for (x, y, w, h) in detections
        ]

    @staticmethod
    def crop_face(frame, face_rect, margin=0.25):
        """
        Cut out the face region with a little margin around it.
        The margin helps the age model, which expects some context
        (hair, chin, forehead) around the face.

        Returns the cropped BGR image, or None if the rect is invalid.
        """
        if frame is None or face_rect is None:
            return None

        x, y, w, h = face_rect
        frame_h, frame_w = frame.shape[:2]

        # Expand the box by `margin` on every side, clamped to the frame.
        mx, my = int(w * margin), int(h * margin)
        x1 = max(0, x - mx)
        y1 = max(0, y - my)
        x2 = min(frame_w, x + w + mx)
        y2 = min(frame_h, y + h + my)

        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2].copy()
