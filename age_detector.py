"""
age_detector.py — AI Age Estimation module
==========================================
Part of: AI Smart Car Access System (Class 10 AI Project)

Uses the DeepFace library to estimate a person's age from a face image.
DeepFace automatically downloads its pre-trained age model
(~500 MB, one time only) to  ~/.deepface/weights/  on first run.

IMPORTANT DISCLAIMER
--------------------
Age estimation from a face is APPROXIMATE, not legally accurate.
Real systems would use licences, ID cards, or registered driver
profiles. This module exists only to demonstrate the AI concept.

Classes:
    AgeResult   — a small container for one final result.
    AgeDetector — loads the model and estimates age from face crops.
"""

import random
import statistics


class AgeResult:
    """The final, aggregated age decision for one scan."""

    def __init__(self, age, confidence, samples):
        self.age = age                # median estimated age (years)
        self.confidence = confidence  # consistency score 0–100 (see below)
        self.samples = samples        # the raw per-frame estimates

    @property
    def is_adult(self):
        """True if the estimated age is 18 or above."""
        return self.age >= 18


class AgeDetector:
    """
    Wraps DeepFace age estimation.

    Design notes (why it's built this way):
    * DeepFace is imported lazily inside load() — importing TensorFlow
      takes several seconds, so we do it during the boot screen, not
      at program start.
    * A single frame's estimate is noisy, so the app collects SEVERAL
      samples and this class aggregates them with the median.
    * demo_mode lets you rehearse the presentation without installing
      the heavy AI libraries — it returns pretend ages.
    """

    # How many face samples the app should collect before deciding.
    SAMPLES_NEEDED = 5

    def __init__(self, demo_mode=False):
        self.demo_mode = demo_mode
        self.loaded = False
        self._deepface = None
        self._demo_age = None  # fixed per-scan pretend age in demo mode

    # ------------------------------------------------------------------ #
    #  Model loading
    # ------------------------------------------------------------------ #
    def load(self):
        """
        Import DeepFace and warm up the age model.

        Returns:
            (ok, message) — ok is True if the detector is usable.
        """
        if self.demo_mode:
            self.loaded = True
            return True, "Demo mode — using simulated age values (no AI model)."

        try:
            # Heavy import: pulls in TensorFlow. Done once, during boot.
            from deepface import DeepFace
            self._deepface = DeepFace

            # Warm-up call: forces DeepFace to download/load the age model
            # NOW instead of during the first real scan.
            import numpy as np
            dummy = np.zeros((96, 96, 3), dtype="uint8")
            self._deepface.analyze(
                img_path=dummy,
                actions=["age"],
                enforce_detection=False,  # dummy image has no face — that's fine
                silent=True,
            )
            self.loaded = True
            return True, "DeepFace age model loaded successfully."

        except ImportError:
            return False, (
                "DeepFace is not installed. Run:  pip install deepface tf-keras\n"
                "Or start the app with  --demo  to simulate age estimation."
            )
        except Exception as error:  # model download failure, etc.
            return False, f"AI model failed to load: {error}"

    # ------------------------------------------------------------------ #
    #  Per-frame estimation
    # ------------------------------------------------------------------ #
    def estimate(self, face_bgr):
        """
        Estimate age from ONE cropped face image (BGR, from OpenCV).

        Returns:
            float age in years, or None if estimation failed.
        """
        if not self.loaded:
            return None

        if self.demo_mode:
            return self._demo_estimate()

        try:
            results = self._deepface.analyze(
                img_path=face_bgr,
                actions=["age"],
                enforce_detection=False,  # we already detected the face ourselves
                detector_backend="skip",  # the crop IS the face — skip re-detection
                silent=True,
            )
            # DeepFace returns a list with one dict per face.
            if results and "age" in results[0]:
                return float(results[0]["age"])
        except Exception:
            pass  # a single bad frame is not a problem — we sample many
        return None

    def _demo_estimate(self):
        """Produce believable pretend ages for rehearsals (demo mode)."""
        if self._demo_age is None:
            # Pick one pretend "person" per scan: teen or adult, 50/50.
            self._demo_age = random.choice([random.uniform(13, 16),
                                            random.uniform(21, 45)])
        # Add per-frame noise so it looks like real AI output.
        return self._demo_age + random.uniform(-2.0, 2.0)

    def reset_scan(self):
        """Call at the start of every new scan (relevant for demo mode)."""
        self._demo_age = None

    # ------------------------------------------------------------------ #
    #  Aggregation
    # ------------------------------------------------------------------ #
    @staticmethod
    def aggregate(samples):
        """
        Combine several per-frame estimates into one AgeResult.

        * age        = median of samples (robust against outliers)
        * confidence = a CONSISTENCY score: if all frames agree, it's high;
                       if estimates jump around, it's low. This is honest —
                       the model gives no true probability, so we report
                       how stable its answers were instead.
        """
        if not samples:
            return None

        age = statistics.median(samples)

        if len(samples) > 1:
            spread = statistics.stdev(samples)
            # 0 spread → 97%. Each year of disagreement costs ~9 points.
            confidence = max(35.0, min(97.0, 97.0 - spread * 9.0))
        else:
            confidence = 50.0  # single sample = low trust

        return AgeResult(round(age, 1), round(confidence, 1), list(samples))
