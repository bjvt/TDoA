import os
import select
import time
import subprocess
from datetime import datetime

# === Configuration ===
PPS_DEVICE = "/dev/pps0"
AUDIO_DEVICE = "default"   # Use `arecord -L` or `sox -V` to check device name
RECORD_SECONDS = 59 * 60 + 55  # 59 minutes 55 seconds
GAP_SECONDS = 5
OUTPUT_DIR = "/home/pi/recordings"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def wait_for_pps():
    """Waits for the next PPS pulse on /dev/pps0"""
    fd = os.open(PPS_DEVICE, os.O_RDONLY)
    poller = select.poll()
    poller.register(fd, select.POLLPRI)
    poller.poll()
    os.close(fd)

def record_audio(start_time):
    """Records audio starting at the given UTC time"""
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    filename = f"nfc_{timestamp}.wav"
    filepath = os.path.join(OUTPUT_DIR, filename)
    print(f"[{datetime.utcnow()}] Starting recording: {filepath}")

    subprocess.run([
        "sox", "-t", "alsa", AUDIO_DEVICE,
        filepath, "trim", "0", str(RECORD_SECONDS)
    ])

    print(f"[{datetime.utcnow()}] Finished recording: {filepath}")

def main():
    print("Waiting for GPS PPS signal to sync recordings...")

    while True:
        wait_for_pps()
        now = datetime.utcnow()

        # Only record between 22:00 and 05:59 UTC
        if now.hour >= 22 or now.hour < 6:
            record_audio(now)
            print(f"Sleeping {GAP_SECONDS} seconds before next PPS sync...")
            time.sleep(GAP_SECONDS)
        else:
            print(f"[{now}] Outside recording window. Skipping.")
            time.sleep(60)

if __name__ == "__main__":
    main()
