# AI Smart Car Access System

A Class 10 AI school project that simulates an AI-powered car access
control system. The laptop screen acts as the car's **infotainment
display** and the webcam acts as the **in-car driver camera**. The AI
estimates the driver's age from their face — if the driver appears to
be **18 or older**, the (simulated) engine starts; otherwise the engine
stays locked.

> **The story behind it:** my younger brother once took our family car
> without our parents' permission. This project demonstrates how AI
> could help reduce unauthorized driving by minors.

> ⚠️ **Disclaimer:** This is an educational prototype only. AI age
> estimation from a face is **approximate and NOT legally accurate**.
> A real system would use driving licences, registered driver profiles,
> or ID verification — never face-based age guessing alone.

---

## Screens & Flow

```
Opening animation (System Booting → Checking Camera → Loading AI Model → Ready)
        ↓
Press START SCAN
        ↓
Camera detects your face (green HUD box)
        ↓
"Estimating Age..." (AI samples 5 frames, animated scan line)
        ↓
DECISION
  ├── Age ≥ 18 → ✔ ACCESS GRANTED (green screen, steering wheel,
  │              speedometer sweep, loading bar, startup sound,
  │              "Engine Started Successfully")
  └── Age < 18 → ✖ ACCESS DENIED (red screen, animated lock,
                 warning sound, "Please ask an adult to drive.")
```

Error handling: **"No Face Detected"** if nobody is visible,
**"Only one driver allowed."** if two or more faces are seen, and a
timeout if the face can't be read within 40 seconds.

---

## Project Structure

```
AI_Smart_Car_Access_System/
├── main.py            # entry point — run this
├── ui.py              # futuristic Tkinter dashboard (all screens/animations)
├── camera.py          # webcam + OpenCV face detection
├── age_detector.py    # DeepFace age estimation + sample aggregation
├── requirements.txt
├── README.md
└── assets/
    ├── icons/logo.png         # boot-screen logo
    └── sounds/                # startup.wav, warning.wav, scan.wav
```

---

## Installation

**Requirements:** Python 3.9 – 3.12, a webcam, internet (first run only).

```bash
# 1. Go into the project folder
cd AI_Smart_Car_Access_System

# 2. (Recommended) create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install the libraries
pip install -r requirements.txt
```

**Linux only:** if Tkinter is missing, run `sudo apt install python3-tk`.

### The AI model download (automatic)

You do **not** need to download any model manually. On the very first
run, DeepFace automatically downloads its pre-trained age model
(~500 MB total, including its face model) into:

```
~/.deepface/weights/          (your home folder)
```

This happens once, during the "Loading AI Model..." boot step —
so the first launch is slow (2–5 min depending on internet). Every
later launch loads from disk in a few seconds. No configuration needed.

---

## How to Run

```bash
python main.py               # full AI mode
python main.py --demo        # demo mode — UI works WITHOUT DeepFace (simulated ages)
python main.py --camera 1    # if you have more than one webcam
```

**Demo mode** is perfect for rehearsing the exhibition presentation on
a computer where the AI libraries aren't installed — everything works,
but ages are simulated (it randomly acts as a teen or an adult).

**macOS note:** the first launch will ask for camera permission —
click Allow (System Settings → Privacy & Security → Camera).

---

## How the AI Works

1. **Face detection (OpenCV):** every frame from the webcam is scanned
   with a *Haar Cascade classifier* — a classic computer-vision
   algorithm that finds face-like patterns of light and dark regions.
   It runs on a half-size grayscale copy of the frame so it stays fast.

2. **Age estimation (DeepFace):** when you press START SCAN, the
   detected face is cropped (with a small margin) and passed to
   DeepFace's age model — a *convolutional neural network (CNN)*
   pre-trained on thousands of labelled face photos. The network
   outputs a probability for each age and returns the expected value.

3. **Sampling + median:** one frame's guess is noisy, so the app
   collects **5 estimates** from different frames and takes the
   **median** (robust against outliers).

4. **Consistency score:** the model gives no true "confidence", so the
   app honestly reports how much the 5 estimates *agreed with each
   other* (low spread = high consistency).

5. **Decision:** median age ≥ 18 → ACCESS GRANTED; otherwise ACCESS
   DENIED and the engine stays locked.

---

## Limitations (be honest at the exhibition!)

- **Age estimation is approximate** — typical error is ±4–8 years, and
  it is worst for teenagers, which is exactly the boundary this project
  cares about. A 16-year-old can read as 20 and vice-versa.
- Accuracy varies with **lighting, camera quality, angle, glasses,
  and makeup**, and can differ across skin tones and demographics
  (a known fairness issue in face-analysis AI).
- It can be **fooled** — e.g. showing a photo of an adult to the
  camera. Real systems need liveness detection.
- This is a **simulation**: no real car hardware is controlled.
- Face-based age checks alone would **not be legally acceptable** for
  vehicle access anywhere.

---

## Future Improvements

- **Face recognition** of registered family drivers (match against
  saved profiles instead of guessing age) using the `face_recognition`
  library.
- **Liveness detection** (blink detection) to block photo attacks.
- Two-factor access: face + PIN on the dashboard.
- Connect to real hardware — a relay/Arduino to control an actual motor.
- Log every access attempt with a snapshot, and send parents a phone
  notification when access is denied.
- Try newer, more accurate age models (e.g. MiVOLO) as they become
  available.

---

*Built with Python, OpenCV, DeepFace, Tkinter, Pillow and NumPy.*
