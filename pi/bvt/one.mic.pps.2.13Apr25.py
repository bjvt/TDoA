import os
import time
import subprocess
from datetime import datetime, timedelta
import pytz

# === Configuration ===
AUDIO_DEVICE = "default"   # Run `arecord -L` or `sox -V` to check
RECORD_SECONDS = 59 * 60 + 55  # 59 minutes 55 seconds
GAP_SECONDS = 5
OUTPUT_DIR = "/home/pi/recordings"

# Use US/Eastern time zone
local_tz = pytz.timezone('US/Eastern')

# Make output directory if needed
os.makedirs(OUTPUT_DIR, exist_ok=True)

def is_recording_time(now):
    # Returns True if time is between 22:00 and 06:00 EST
    hour = now.hour
    return hour >= 22 or hour < 6

def record_audio(start_time):
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    filename = f"nfc_{timestamp}.wav"
    filepath = os.path.join(OUTPUT_DIR, filename)

    print(f"[{datetime.utcnow()}] Start recording: {filepath}")
    subprocess.run([
        "sox", "-t", "alsa", AUDIO_DEVICE,
        filepath, "trim", "0", str(RECORD_SECONDS)
    ])
    print(f"[{datetime.utcnow()}] Finished: {filepath}")

def main():
    print("Starting AudioMoth-style PPS-synced recorder...")

    while True:
        # Get time in EST
        now_utc = datetime.utcnow()
        now_est = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)

        if is_recording_time(now_est):
            record_audio(now_utc)
            time.sleep(GAP_SECONDS)
        else:
            print(f"[{now_est.strftime('%H:%M:%S')}] Outside recording window.")
            time.sleep(60)

if __name__ == "__main__":
    main()

