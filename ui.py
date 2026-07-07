"""
ui.py — Futuristic Infotainment Dashboard
=========================================
Part of: AI Smart Car Access System (Class 10 AI Project)

The laptop screen acts as the car's infotainment display.
Built with plain Tkinter (no extra UI library needed) styled to look
like a Tesla / Mercedes-style dark dashboard:

    * dark theme with blue neon accents
    * glassmorphism-style cards
    * rounded canvas buttons
    * animated boot screen, scan line, progress bars
    * green ACCESS GRANTED / red ACCESS DENIED screens
    * canvas-drawn steering wheel, lock and speedometer icons

Classes:
    SoundPlayer   — cross-platform, non-blocking WAV playback.
    RoundedButton — a rounded, glowing canvas button.
    GlassCard     — a translucent-looking panel with a title.
    DashboardApp  — the whole application (state machine + screens).
"""

import os
import platform
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime

import cv2
from PIL import Image, ImageTk

from age_detector import AgeDetector

# --------------------------------------------------------------------------- #
#  Theme — one place to change every colour in the app
# --------------------------------------------------------------------------- #
C = {
    "bg":        "#070B14",  # near-black blue background
    "bg2":       "#0B1220",  # slightly lighter panel background
    "card":      "#101A2E",  # glass card fill
    "card_edge": "#1E3A5F",  # glass card border
    "neon":      "#00D4FF",  # main blue neon accent
    "neon_dim":  "#0E5A75",
    "text":      "#E8F1FF",  # main text
    "muted":     "#7E93B8",  # secondary text
    "good":      "#22E06C",  # green (access granted)
    "good_dark": "#062B15",
    "bad":       "#FF3B4E",  # red (access denied)
    "bad_dark":  "#2B060A",
    "warn":      "#FFC24B",  # amber (warnings)
}

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")


def FONT(size, bold=False):
    """Pick a modern font that exists on this OS."""
    family = "Segoe UI" if platform.system() == "Windows" else "Helvetica Neue"
    return (family, size, "bold" if bold else "normal")


# --------------------------------------------------------------------------- #
#  Sound
# --------------------------------------------------------------------------- #
class SoundPlayer:
    """Plays WAV files without freezing the UI (each play runs in a thread)."""

    @staticmethod
    def play(filename):
        path = os.path.join(SOUNDS_DIR, filename)
        if not os.path.exists(path):
            return  # sounds are optional — never crash over a missing file
        threading.Thread(target=SoundPlayer._play_blocking,
                         args=(path,), daemon=True).start()

    @staticmethod
    def _play_blocking(path):
        system = platform.system()
        try:
            if system == "Windows":
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME)
            elif system == "Darwin":  # macOS
                subprocess.run(["afplay", path], check=False)
            else:  # Linux — try the two most common players
                for player in (["aplay", "-q"], ["paplay"]):
                    try:
                        subprocess.run(player + [path], check=True)
                        break
                    except (FileNotFoundError, subprocess.CalledProcessError):
                        continue
        except Exception:
            pass  # sound is a bonus feature, never fatal


# --------------------------------------------------------------------------- #
#  Reusable widgets
# --------------------------------------------------------------------------- #
class RoundedButton(tk.Canvas):
    """A rounded rectangle button with a neon glow on hover."""

    def __init__(self, parent, text, command=None, width=190, height=52,
                 color=C["neon"], text_color="#04121A", bg=C["bg"]):
        super().__init__(parent, width=width, height=height,
                         bg=bg, highlightthickness=0)
        self.command = command
        self.color = color
        self.text_color = text_color
        self.w, self.h = width, height
        self.enabled = True

        self._draw(self.color)
        self.text_id = self.create_text(width // 2, height // 2, text=text,
                                        fill=text_color, font=FONT(13, bold=True))
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self.enabled and self._draw("#66E5FF"
                  if self.color == C["neon"] else self.color))
        self.bind("<Leave>", lambda e: self._draw(self.color if self.enabled
                                                  else C["neon_dim"]))

    def _draw(self, fill):
        self.delete("shape")
        r = self.h // 2  # full pill shape
        x1, y1, x2, y2 = 2, 2, self.w - 2, self.h - 2
        self.create_oval(x1, y1, x1 + 2 * r, y2, fill=fill, outline=fill,
                         tags="shape")
        self.create_oval(x2 - 2 * r, y1, x2, y2, fill=fill, outline=fill,
                         tags="shape")
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=fill,
                              tags="shape")
        self.tag_lower("shape")

    def _on_click(self, _event):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._draw(self.color if enabled else C["neon_dim"])
        self.itemconfig(self.text_id,
                        fill=self.text_color if enabled else C["muted"])


class GlassCard(tk.Frame):
    """A dark 'glassmorphism' card: subtle fill, glowing border, title row."""

    def __init__(self, parent, title, icon=""):
        super().__init__(parent, bg=C["card"],
                         highlightbackground=C["card_edge"],
                         highlightthickness=1)
        header = tk.Frame(self, bg=C["card"])
        header.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(header, text=f"{icon}  {title}".strip(), font=FONT(11, bold=True),
                 fg=C["neon"], bg=C["card"]).pack(side="left")

        # thin neon divider line under the title
        tk.Frame(self, bg=C["card_edge"], height=1).pack(fill="x", padx=14)

        self.body = tk.Frame(self, bg=C["card"])
        self.body.pack(fill="both", expand=True, padx=14, pady=10)

    def add_row(self, label):
        """Add a 'Label: value' row; returns the value Label to update later."""
        row = tk.Frame(self.body, bg=C["card"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, font=FONT(10), fg=C["muted"],
                 bg=C["card"]).pack(side="left")
        value = tk.Label(row, text="—", font=FONT(10, bold=True),
                         fg=C["text"], bg=C["card"])
        value.pack(side="right")
        return value


# --------------------------------------------------------------------------- #
#  Main application
# --------------------------------------------------------------------------- #
class DashboardApp:
    """
    The full dashboard. Runs as a simple STATE MACHINE:

        BOOT → IDLE → SCANNING → ANALYZING → GRANTED / DENIED → (reset) IDLE
    """

    PREVIEW_W, PREVIEW_H = 760, 430   # camera preview size in pixels
    SCAN_TIMEOUT = 40                 # seconds before a scan gives up

    def __init__(self, root, camera, detector, demo_mode=False):
        self.root = root
        self.camera = camera
        self.detector = detector
        self.demo_mode = demo_mode

        # ---- state machine ----
        self.state = "BOOT"
        self.samples = []                 # age estimates collected this scan
        self.samples_lock = threading.Lock()
        self.scan_started_at = 0.0
        self.analyzing_busy = False       # is the AI thread busy right now?
        self.scanline_y = 0               # animated scan line position
        self.result = None                # final AgeResult
        self._photo = None                # keep a reference or Tk drops the image
        self._closing = False

        # ---- window ----
        root.title("AI Smart Car Access System")
        root.configure(bg=C["bg"])
        root.geometry("1280x800")
        root.minsize(1150, 720)

        self._build_boot_screen()
        self.root.after(80, self._boot_sequence)

    # ====================================================================== #
    #  BOOT SCREEN
    # ====================================================================== #
    def _build_boot_screen(self):
        self.boot = tk.Frame(self.root, bg=C["bg"])
        self.boot.pack(fill="both", expand=True)

        center = tk.Frame(self.boot, bg=C["bg"])
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Logo (generated PNG if present, else a drawn fallback)
        logo_path = os.path.join(ICONS_DIR, "logo.png")
        if os.path.exists(logo_path):
            img = Image.open(logo_path).resize((110, 110), Image.LANCZOS)
            self._logo = ImageTk.PhotoImage(img)
            tk.Label(center, image=self._logo, bg=C["bg"]).pack(pady=(0, 14))

        tk.Label(center, text="AI SMART CAR ACCESS", font=FONT(28, bold=True),
                 fg=C["text"], bg=C["bg"]).pack()
        tk.Label(center, text="INTELLIGENT DRIVER VERIFICATION SYSTEM",
                 font=FONT(11), fg=C["neon"], bg=C["bg"]).pack(pady=(4, 30))

        self.boot_status = tk.Label(center, text="System Booting...",
                                    font=FONT(12), fg=C["muted"], bg=C["bg"])
        self.boot_status.pack()

        self.boot_bar = tk.Canvas(center, width=420, height=8, bg=C["bg2"],
                                  highlightthickness=0)
        self.boot_bar.pack(pady=14)
        self.boot_fill = self.boot_bar.create_rectangle(0, 0, 0, 8,
                                                        fill=C["neon"], width=0)

        tk.Label(center,
                 text="Educational prototype — AI age estimation is approximate,\n"
                      "not legally accurate.",
                 font=FONT(9), fg=C["muted"], bg=C["bg"],
                 justify="center").pack(pady=(24, 0))

    def _boot_progress(self, fraction, message):
        """Update the boot bar + status text (must run on the UI thread)."""
        self.boot_status.config(text=message)
        self.boot_bar.coords(self.boot_fill, 0, 0, int(420 * fraction), 8)

    def _boot_sequence(self):
        """
        Boot flow: System Booting → Checking Camera → Loading AI Model → Ready.
        Camera + model loading run in a background thread so the bar
        keeps animating smoothly.
        """
        def work():
            steps = []

            self._ui(lambda: self._boot_progress(0.15, "System Booting..."))
            time.sleep(0.9)

            self._ui(lambda: self._boot_progress(0.35, "Checking Camera..."))
            camera_ok = self.camera.open()
            steps.append(("camera", camera_ok,
                          "Camera online." if camera_ok
                          else "Camera not found — check webcam permissions."))
            time.sleep(0.6)

            self._ui(lambda: self._boot_progress(
                0.55, "Loading AI Model...  (first run may download ~500 MB)"))
            model_ok, model_msg = self.detector.load()
            steps.append(("model", model_ok, model_msg))

            self._ui(lambda: self._boot_progress(0.9, "Finalizing..."))
            time.sleep(0.5)
            self._ui(lambda: self._boot_progress(1.0, "Ready"))
            time.sleep(0.6)

            self._ui(lambda: self._finish_boot(steps))

        threading.Thread(target=work, daemon=True).start()

    def _finish_boot(self, steps):
        self.boot.destroy()
        self._build_dashboard()
        self.state = "IDLE"

        for name, ok, msg in steps:
            self.log(msg, "ok" if ok else "err")
            if name == "camera" and not ok:
                self.status_value.config(text="CAMERA ERROR", fg=C["bad"])
                self.scan_btn.set_enabled(False)
            if name == "model" and not ok:
                self.ai_status_value.config(text="MODEL ERROR", fg=C["bad"])
                self.scan_btn.set_enabled(False)

        if self.demo_mode:
            self.log("DEMO MODE — ages are simulated, no AI model in use.", "warn")

        self.log("System ready. Press START SCAN to verify the driver.", "info")
        self._update_loop()
        self._tick_clock()

    # ====================================================================== #
    #  MAIN DASHBOARD LAYOUT
    # ====================================================================== #
    def _build_dashboard(self):
        self.main = tk.Frame(self.root, bg=C["bg"])
        self.main.pack(fill="both", expand=True)

        # ---------- top bar ----------
        top = tk.Frame(self.main, bg=C["bg2"], height=64)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="⬢", font=FONT(22), fg=C["neon"],
                 bg=C["bg2"]).pack(side="left", padx=(18, 6))
        tk.Label(top, text="AI SMART CAR ACCESS", font=FONT(15, bold=True),
                 fg=C["text"], bg=C["bg2"]).pack(side="left")
        mode = "DEMO MODE" if self.demo_mode else "AI MODE"
        tk.Label(top, text=f"● {mode}", font=FONT(9, bold=True),
                 fg=C["warn"] if self.demo_mode else C["good"],
                 bg=C["bg2"]).pack(side="left", padx=14)

        self.clock_label = tk.Label(top, text="", font=FONT(15, bold=True),
                                    fg=C["neon"], bg=C["bg2"])
        self.clock_label.pack(side="right", padx=18)
        self.date_label = tk.Label(top, text="", font=FONT(10),
                                   fg=C["muted"], bg=C["bg2"])
        self.date_label.pack(side="right")

        # ---------- middle: preview (left) + panels (right) ----------
        middle = tk.Frame(self.main, bg=C["bg"])
        middle.pack(fill="both", expand=True, padx=16, pady=12)

        preview_card = GlassCard(middle, "IN-CAR CAMERA — DRIVER SEAT", icon="📷")
        preview_card.pack(side="left", fill="both", expand=True)

        self.preview = tk.Canvas(preview_card.body, width=self.PREVIEW_W,
                                 height=self.PREVIEW_H, bg="#02050A",
                                 highlightthickness=0)
        self.preview.pack(fill="both", expand=True)

        self.preview_caption = tk.Label(preview_card.body,
                                        text="Camera feed live — waiting for scan",
                                        font=FONT(10), fg=C["muted"], bg=C["card"])
        self.preview_caption.pack(anchor="w", pady=(8, 0))

        right = tk.Frame(middle, bg=C["bg"], width=330)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        # STATUS panel
        status_card = GlassCard(right, "SYSTEM STATUS", icon="⚡")
        status_card.pack(fill="x", pady=(0, 10))
        self.status_value = status_card.add_row("State")
        self.face_value = status_card.add_row("Face Detection")
        self.recog_value = status_card.add_row("Recognition")
        self.status_value.config(text="IDLE", fg=C["neon"])

        # AGE ESTIMATION panel
        age_card = GlassCard(right, "AGE ESTIMATION (AI)", icon="🧠")
        age_card.pack(fill="x", pady=(0, 10))
        self.age_value = age_card.add_row("Estimated Age")
        self.conf_value = age_card.add_row("Consistency")
        self.ai_status_value = age_card.add_row("AI Model")
        self.ai_status_value.config(
            text="DEMO" if self.demo_mode else "DeepFace", fg=C["good"])
        self.scan_bar = tk.Canvas(age_card.body, width=270, height=6,
                                  bg=C["bg2"], highlightthickness=0)
        self.scan_bar.pack(fill="x", pady=(8, 2))
        self.scan_bar_fill = self.scan_bar.create_rectangle(
            0, 0, 0, 6, fill=C["neon"], width=0)
        tk.Label(age_card.body, text="Estimates are approximate — not legal ID.",
                 font=FONT(8), fg=C["muted"], bg=C["card"]).pack(anchor="w")

        # SECURITY panel
        sec_card = GlassCard(right, "VEHICLE SECURITY", icon="🛡")
        sec_card.pack(fill="x", pady=(0, 10))
        self.engine_value = sec_card.add_row("Engine")
        self.access_value = sec_card.add_row("Access")
        self.policy_value = sec_card.add_row("Policy")
        self.engine_value.config(text="LOCKED", fg=C["bad"])
        self.access_value.config(text="NOT VERIFIED", fg=C["warn"])
        self.policy_value.config(text="Driver must be 18+")

        # SYSTEM LOGS panel
        log_card = GlassCard(right, "SYSTEM LOGS", icon="≡")
        log_card.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_card.body, height=8, bg=C["bg2"],
                                fg=C["text"], font=("Courier New", 9),
                                relief="flat", state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
        for tag, color in (("info", C["muted"]), ("ok", C["good"]),
                           ("warn", C["warn"]), ("err", C["bad"])):
            self.log_text.tag_config(tag, foreground=color)

        # ---------- bottom navigation bar (luxury-car style) ----------
        nav = tk.Frame(self.main, bg=C["bg2"], height=86)
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)

        inner = tk.Frame(nav, bg=C["bg2"])
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self.scan_btn = RoundedButton(inner, "▶  START SCAN",
                                      command=self.start_scan, bg=C["bg2"])
        self.scan_btn.pack(side="left", padx=10)
        self.reset_btn = RoundedButton(inner, "⟲  RESET", command=self.reset,
                                       width=140, color=C["card_edge"],
                                       text_color=C["text"], bg=C["bg2"])
        self.reset_btn.pack(side="left", padx=10)
        self.exit_btn = RoundedButton(inner, "⏻  EXIT", width=130,
                                      command=self._exit, color=C["bad_dark"],
                                      text_color=C["bad"], bg=C["bg2"])
        self.exit_btn.pack(side="left", padx=10)

    # ====================================================================== #
    #  CLOCK + LOGGING
    # ====================================================================== #
    def _tick_clock(self):
        if self._closing:
            return
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%a, %d %b %Y"))
        self.root.after(1000, self._tick_clock)

    def log(self, message, level="info"):
        """Append a timestamped line to the SYSTEM LOGS panel."""
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{stamp}] {message}\n", level)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _ui(self, func):
        """Safely run `func` on the Tk thread (from worker threads)."""
        if not self._closing:
            self.root.after(0, func)

    # ====================================================================== #
    #  LIVE CAMERA LOOP (runs ~30x per second via root.after)
    # ====================================================================== #
    def _update_loop(self):
        if self._closing:
            return

        ok, frame, faces = self.camera.read()
        if ok:
            self._process_state(frame, faces)
            self._draw_preview(frame, faces)

        self.root.after(33, self._update_loop)

    def _process_state(self, frame, faces):
        """The heart of the app: what to do in each state, every frame."""
        n = len(faces)

        # -- live face status (shown in every state) --
        if n == 0:
            self.face_value.config(text="No Face Detected", fg=C["warn"])
        elif n == 1:
            self.face_value.config(text="Face Detected ✓", fg=C["good"])
        else:
            self.face_value.config(text=f"{n} Faces — one driver only!",
                                   fg=C["bad"])

        if self.state != "SCANNING":
            return

        # -- scanning: collect age samples --
        elapsed = time.time() - self.scan_started_at
        if elapsed > self.SCAN_TIMEOUT:
            self._scan_failed("Scan timed out — face not readable. Try again "
                              "with better lighting.")
            return

        if n == 0:
            self.preview_caption.config(text="No Face Detected — please look "
                                             "at the camera", fg=C["warn"])
            return
        if n > 1:
            self.preview_caption.config(text="Only one driver allowed.",
                                        fg=C["bad"])
            return

        self.preview_caption.config(text="Estimating Age...", fg=C["neon"])

        # Send at most ONE face crop to the AI at a time (it's slow).
        if not self.analyzing_busy:
            face_crop = self.camera.crop_face(frame, faces[0])
            if face_crop is not None:
                self.analyzing_busy = True
                threading.Thread(target=self._analyze_worker,
                                 args=(face_crop,), daemon=True).start()

        # progress bar + decision check
        with self.samples_lock:
            count = len(self.samples)
        needed = AgeDetector.SAMPLES_NEEDED
        frac = min(1.0, count / needed)
        width = self.scan_bar.winfo_width() or 270
        self.scan_bar.coords(self.scan_bar_fill, 0, 0, int(width * frac), 6)

        if count >= needed:
            self._decide()

    def _analyze_worker(self, face_crop):
        """Background thread: one AI age estimate for one face crop."""
        age = self.detector.estimate(face_crop)
        if age is not None:
            with self.samples_lock:
                self.samples.append(age)
            # show the running estimate live
            self._ui(lambda: self.age_value.config(
                text=f"~ {age:.0f} yrs (sampling...)", fg=C["neon"]))
        self.analyzing_busy = False

    # ====================================================================== #
    #  PREVIEW DRAWING
    # ====================================================================== #
    def _draw_preview(self, frame, faces):
        cw = self.preview.winfo_width()
        ch = self.preview.winfo_height()
        if cw < 50 or ch < 50:
            return  # window not fully laid out yet — skip this frame

        # letterbox-fit the frame into the canvas
        fh, fw = frame.shape[:2]
        scale = min(cw / fw, ch / fh)
        new_w, new_h = int(fw * scale), int(fh * scale)
        resized = cv2.resize(frame, (new_w, new_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        self._photo = ImageTk.PhotoImage(Image.fromarray(rgb))

        self.preview.delete("all")
        ox, oy = (cw - new_w) // 2, (ch - new_h) // 2
        self.preview.create_image(ox, oy, image=self._photo, anchor="nw")

        # green face boxes with HUD corner brackets
        for (x, y, w, h) in faces:
            x1, y1 = ox + int(x * scale), oy + int(y * scale)
            x2, y2 = ox + int((x + w) * scale), oy + int((y + h) * scale)
            color = C["good"] if len(faces) == 1 else C["bad"]
            k = max(12, (x2 - x1) // 6)  # bracket length
            for (ax, ay, bx, by) in (
                (x1, y1, x1 + k, y1), (x1, y1, x1, y1 + k),          # top-left
                (x2, y1, x2 - k, y1), (x2, y1, x2, y1 + k),          # top-right
                (x1, y2, x1 + k, y2), (x1, y2, x1, y2 - k),          # bottom-left
                (x2, y2, x2 - k, y2), (x2, y2, x2, y2 - k),          # bottom-right
            ):
                self.preview.create_line(ax, ay, bx, by, fill=color, width=3)
            self.preview.create_rectangle(x1, y1, x2, y2, outline=color, width=1)
            if len(faces) == 1:
                self.preview.create_text(x1, y1 - 12, text="DRIVER",
                                         fill=color, font=FONT(9, bold=True),
                                         anchor="w")

        # animated AI scan line while scanning
        if self.state == "SCANNING":
            self.scanline_y = (self.scanline_y + 6) % ch
            y = self.scanline_y
            self.preview.create_line(0, y, cw, y, fill=C["neon"], width=2)
            self.preview.create_line(0, y + 3, cw, y + 3,
                                     fill=C["neon_dim"], width=1)
            self.preview.create_text(cw - 12, 16, text="● AI SCANNING",
                                     fill=C["neon"], font=FONT(10, bold=True),
                                     anchor="e")

    # ====================================================================== #
    #  SCAN FLOW
    # ====================================================================== #
    def start_scan(self):
        if self.state not in ("IDLE",):
            return
        self.state = "SCANNING"
        with self.samples_lock:
            self.samples = []
        self.detector.reset_scan()
        self.scan_started_at = time.time()
        self.result = None

        self.status_value.config(text="SCANNING", fg=C["neon"])
        self.age_value.config(text="Estimating...", fg=C["neon"])
        self.conf_value.config(text="—", fg=C["text"])
        self.recog_value.config(text="Verifying driver...", fg=C["neon"])
        self.scan_btn.set_enabled(False)
        SoundPlayer.play("scan.wav")
        self.log("Scan started — collecting AI age samples...", "info")

    def _scan_failed(self, reason):
        self.state = "IDLE"
        self.scan_btn.set_enabled(True)
        self.status_value.config(text="IDLE", fg=C["neon"])
        self.recog_value.config(text="Not verified", fg=C["warn"])
        self.preview_caption.config(text="Camera feed live — waiting for scan",
                                    fg=C["muted"])
        self.log(reason, "warn")

    def _decide(self):
        """All samples collected → aggregate and show the decision screen."""
        self.state = "ANALYZING"
        with self.samples_lock:
            result = AgeDetector.aggregate(self.samples)
        self.result = result

        if result is None:
            self._scan_failed("Could not estimate age — please try again.")
            return

        self.age_value.config(text=f"{result.age:.1f} years",
                              fg=C["good"] if result.is_adult else C["bad"])
        self.conf_value.config(text=f"{result.confidence:.0f}%")
        self.log(f"Median age estimate: {result.age:.1f} yrs "
                 f"(consistency {result.confidence:.0f}%, "
                 f"{len(result.samples)} samples)", "info")

        if result.is_adult:
            self.recog_value.config(text="Driver Verified ✓", fg=C["good"])
            self._show_granted()
        else:
            self.recog_value.config(text="Unauthorized Driver", fg=C["bad"])
            self._show_denied()

    # ====================================================================== #
    #  ACCESS GRANTED SCREEN
    # ====================================================================== #
    def _show_granted(self):
        self.state = "GRANTED"
        self.status_value.config(text="ACCESS GRANTED", fg=C["good"])
        self.access_value.config(text="GRANTED ✓", fg=C["good"])
        self.log("ACCESS GRANTED — driver verified as adult.", "ok")
        SoundPlayer.play("startup.wav")

        ov = self._make_overlay(C["good_dark"])
        cv_ = tk.Canvas(ov, bg=C["good_dark"], highlightthickness=0)
        cv_.pack(fill="both", expand=True)
        self._overlay_canvas = cv_
        self.root.after(50, lambda: self._granted_layout(cv_))

    def _granted_layout(self, cv_):
        w = cv_.winfo_width() or 1280
        h = cv_.winfo_height() or 800
        cx = w // 2

        cv_.create_text(cx, h * 0.12, text="✔  ACCESS GRANTED",
                        fill=C["good"], font=FONT(40, bold=True))
        cv_.create_text(cx, h * 0.20, text="Driver Verified   •   Welcome",
                        fill=C["text"], font=FONT(17))
        age_txt = (f"Estimated age: {self.result.age:.1f} yrs   |   "
                   f"consistency {self.result.confidence:.0f}%   "
                   f"(approximate — not legal ID)")
        cv_.create_text(cx, h * 0.26, text=age_txt, fill=C["muted"],
                        font=FONT(11))

        self._draw_steering_wheel(cv_, cx - 260, int(h * 0.52), 95)
        gauge = (cx + 240, int(h * 0.52), 120)
        self._draw_speedometer(cv_, *gauge, speed=0)

        self.engine_msg = cv_.create_text(cx, h * 0.78, text="Engine Starting...",
                                          fill=C["text"], font=FONT(16, bold=True))

        # loading bar
        bar_w = 460
        bx1, by = cx - bar_w // 2, int(h * 0.84)
        cv_.create_rectangle(bx1, by, bx1 + bar_w, by + 12,
                             outline=C["good"], width=1)
        bar = cv_.create_rectangle(bx1 + 2, by + 2, bx1 + 2, by + 10,
                                   fill=C["good"], width=0)

        back = RoundedButton(cv_, "⟲  BACK TO DASHBOARD", command=self.reset,
                             width=240, color=C["good"], text_color="#04140A",
                             bg=C["good_dark"])
        cv_.create_window(cx, int(h * 0.93), window=back)

        self._animate_engine_start(cv_, bar, bx1, bar_w, by, gauge, step=0)

    def _animate_engine_start(self, cv_, bar, bx1, bar_w, by, gauge, step):
        """60 steps ≈ 3 seconds: fill the bar, then sweep the speedometer."""
        if self.state != "GRANTED" or self._closing:
            return
        total = 60
        frac = min(1.0, step / total)
        cv_.coords(bar, bx1 + 2, by + 2, bx1 + 2 + int((bar_w - 4) * frac),
                   by + 10)

        # speedometer needle does a Tesla-style sweep: 0 → 60 → idle 0
        gx, gy, gr = gauge
        if frac < 0.5:
            speed = 0  # needle stays at zero while the bar fills
        else:
            sweep = (frac - 0.5) * 2          # 0 → 1
            speed = int(60 * (1 - abs(2 * sweep - 1)))  # 0 → 60 → 0
        cv_.delete("gauge")
        self._draw_speedometer(cv_, gx, gy, gr, speed=speed)

        if step < total:
            self.root.after(50, lambda: self._animate_engine_start(
                cv_, bar, bx1, bar_w, by, gauge, step + 1))
        else:
            cv_.itemconfig(self.engine_msg, text="Engine Started Successfully ✓")
            self.engine_value.config(text="RUNNING ✓", fg=C["good"])
            self.log("Engine Started Successfully.", "ok")

    # ---- canvas-drawn icons (no image files needed) ----
    def _draw_steering_wheel(self, cv_, x, y, r):
        """A minimalist neon steering wheel."""
        g = C["good"]
        cv_.create_oval(x - r, y - r, x + r, y + r, outline=g, width=5)
        r2 = int(r * 0.32)
        cv_.create_oval(x - r2, y - r2, x + r2, y + r2, outline=g, width=4)
        import math
        for ang in (90, 210, 330):  # three spokes
            a = math.radians(ang)
            cv_.create_line(x + r2 * math.cos(a), y - r2 * math.sin(a),
                            x + (r - 4) * math.cos(a), y - (r - 4) * math.sin(a),
                            fill=g, width=5)
        cv_.create_text(x, y + r + 24, text="STEERING ACTIVE", fill=g,
                        font=FONT(10, bold=True))

    def _draw_speedometer(self, cv_, x, y, r, speed=0):
        """A fake digital speedometer gauge (0–120 km/h)."""
        import math
        g = C["good"]
        # arc from 210° to -30° (a 240° dial)
        cv_.create_arc(x - r, y - r, x + r, y + r, start=-30, extent=240,
                       style="arc", outline=C["card_edge"], width=10,
                       tags="gauge")
        frac = min(1.0, speed / 120.0)
        cv_.create_arc(x - r, y - r, x + r, y + r, start=210,
                       extent=-240 * frac, style="arc", outline=g, width=10,
                       tags="gauge")
        # needle
        ang = math.radians(210 - 240 * frac)
        cv_.create_line(x, y, x + (r - 18) * math.cos(ang),
                        y - (r - 18) * math.sin(ang),
                        fill=C["text"], width=3, tags="gauge")
        cv_.create_text(x, y + int(r * 0.45), text=f"{speed:d}",
                        fill=C["text"], font=FONT(26, bold=True), tags="gauge")
        cv_.create_text(x, y + int(r * 0.45) + 26, text="km/h", fill=C["muted"],
                        font=FONT(10), tags="gauge")

    # ====================================================================== #
    #  ACCESS DENIED SCREEN
    # ====================================================================== #
    def _show_denied(self):
        self.state = "DENIED"
        self.status_value.config(text="ACCESS DENIED", fg=C["bad"])
        self.access_value.config(text="DENIED ✖", fg=C["bad"])
        self.engine_value.config(text="LOCKED", fg=C["bad"])
        self.log("ACCESS DENIED — driver appears under 18. Engine locked.", "err")
        SoundPlayer.play("warning.wav")

        ov = self._make_overlay(C["bad_dark"])
        cv_ = tk.Canvas(ov, bg=C["bad_dark"], highlightthickness=0)
        cv_.pack(fill="both", expand=True)
        self.root.after(50, lambda: self._denied_layout(cv_))

    def _denied_layout(self, cv_):
        w = cv_.winfo_width() or 1280
        h = cv_.winfo_height() or 800
        cx = w // 2

        cv_.create_text(cx, h * 0.12, text="✖  ACCESS DENIED",
                        fill=C["bad"], font=FONT(40, bold=True))
        cv_.create_text(cx, h * 0.20,
                        text="Driver appears under 18   •   Unauthorized Driver",
                        fill=C["text"], font=FONT(16))
        age_txt = (f"Estimated age: {self.result.age:.1f} yrs   |   "
                   f"consistency {self.result.confidence:.0f}%   "
                   f"(approximate — not legal ID)")
        cv_.create_text(cx, h * 0.26, text=age_txt, fill=C["muted"], font=FONT(11))

        cv_.create_text(cx, h * 0.72, text="🔒  ENGINE LOCKED",
                        fill=C["bad"], font=FONT(22, bold=True))
        cv_.create_text(cx, h * 0.79, text="Please ask an adult to drive.",
                        fill=C["warn"], font=FONT(14))

        back = RoundedButton(cv_, "⟲  BACK TO DASHBOARD", command=self.reset,
                             width=240, color=C["bad"], text_color="#1A0406",
                             bg=C["bad_dark"])
        cv_.create_window(cx, int(h * 0.92), window=back)

        # animated lock: shackle drops closed, then the lock pulses red
        self._animate_lock(cv_, cx, int(h * 0.5), step=0)

    def _animate_lock(self, cv_, x, y, step):
        """20 steps: shackle slides down into the lock body, then glow pulses."""
        if self.state != "DENIED" or self._closing:
            return
        cv_.delete("lock")
        r = C["bad"]

        body_w, body_h = 120, 90
        drop = min(1.0, step / 12.0)          # shackle closing progress
        pulse = 3 + 2 * abs((step % 20) - 10) / 10.0  # glow width 3–5

        # glow ring
        cv_.create_oval(x - 110, y - 110, x + 110, y + 110 + 20,
                        outline=r, width=int(pulse), tags="lock")
        # shackle (an arc that slides down as `drop` grows)
        sy = y - 90 + int(28 * drop)
        cv_.create_arc(x - 45, sy - 40, x + 45, sy + 50, start=0, extent=180,
                       style="arc", outline=r, width=10, tags="lock")
        # lock body
        cv_.create_rectangle(x - body_w // 2, y - 10, x + body_w // 2,
                             y - 10 + body_h, outline=r, width=5, tags="lock")
        # keyhole
        cv_.create_oval(x - 10, y + 15, x + 10, y + 35, fill=r, width=0,
                        tags="lock")
        cv_.create_rectangle(x - 4, y + 30, x + 4, y + 55, fill=r, width=0,
                             tags="lock")

        self.root.after(80, lambda: self._animate_lock(cv_, x, y, step + 1))

    # ====================================================================== #
    #  OVERLAY / RESET / EXIT
    # ====================================================================== #
    def _make_overlay(self, bg):
        """A full-window frame that covers the dashboard for decision screens."""
        self.overlay = tk.Frame(self.root, bg=bg)
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        return self.overlay

    def reset(self):
        """Return to the idle dashboard, ready for a new scan."""
        if getattr(self, "overlay", None) is not None:
            self.overlay.destroy()
            self.overlay = None

        self.state = "IDLE"
        with self.samples_lock:
            self.samples = []
        self.result = None
        self.scan_btn.set_enabled(True)
        self.status_value.config(text="IDLE", fg=C["neon"])
        self.recog_value.config(text="—", fg=C["text"])
        self.age_value.config(text="—", fg=C["text"])
        self.conf_value.config(text="—", fg=C["text"])
        self.engine_value.config(text="LOCKED", fg=C["bad"])
        self.access_value.config(text="NOT VERIFIED", fg=C["warn"])
        self.scan_bar.coords(self.scan_bar_fill, 0, 0, 0, 6)
        self.preview_caption.config(text="Camera feed live — waiting for scan",
                                    fg=C["muted"])
        self.log("System reset — ready for next scan.", "info")

    def _exit(self):
        self.shutdown()
        self.root.destroy()

    def shutdown(self):
        """Stop loops and release the webcam cleanly."""
        self._closing = True
        self.camera.release()
