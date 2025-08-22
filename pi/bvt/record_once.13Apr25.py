import os
import subprocess
from datetime import datetime
import argparse

# === Configuration ===
AUDIO_DEVICE = "hw:3,0"
OUTPUT_DIR = "/home/pi/recordings"
LOG_FILE = os.path.join(OUTPUT_DIR, "recording_log.txt")
DEFAULT_MINUTES = 1
DEFAULT_SECONDS = 5

# === Parse CLI arguments ===
parser = argparse.ArgumentParser(description="Record audio with timestamped metadata.")
parser.add_argument('--minutes', type=int, default=DEFAULT_MINUTES, help='Minutes to record')
parser.add_argument('--seconds', type=int, default=DEFAULT_SECONDS, help='Extra seconds to record')
args = parser.parse_args()

RECORD_SECONDS = args.minutes * 60 + args.seconds
os.makedirs(OUTPUT_DIR, exist_ok=True)

def record_audio():
    now = datetime.utcnow()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    microseconds = f"{now.microsecond:06d}"
    unix_time = int(now.timestamp())
    unix_frac = f"{unix_time}.{now.microsecond:06d}"

    filename = f"nfc_{timestamp}_{microseconds}_{unix_time}.wav"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # WAV metadata
    comment = f"Start UTC: {now.isoformat()}Z | PPS-Synced"
    date = now.strftime('%Y-%m-%d')

    print(f"[{now}] Recording: {filepath} ({RECORD_SECONDS} sec)")
    subprocess.run([
        "sox", "-t", "alsa", AUDIO_DEVICE,
        filepath,
        "trim", "0", str(RECORD_SECONDS),
        "--add-comment", f"ICMT={comment}",
        "--add-comment", f"ICRD={date}",
        "--add-comment", "ISFT=AudioMoth Python Script"
    ])
    print(f"[{datetime.utcnow()}] Finished: {filepath}")

    with open(LOG_FILE, "a") as log:
        log.write(
            f"{now.isoformat()}Z UTC - Manual: {filename} ({RECORD_SECONDS}s) - UNIX: {unix_frac}\n"
        )

if __name__ == "__main__":
    record_audio()
