#!/usr/bin/env python3
import json, os, re, signal, subprocess, sys, time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

AUDIO_DEVICE = "hw:1,0"        # adjust with `arecord -l` if needed
RATE = 48000
BITS = 16
CHANNELS = 1
REC_SEC = 59*60 + 55
PAUSE_SEC = 5
BASE_DIR = Path("/data/nfc")
LOCAL_TZ = ZoneInfo("America/New_York")

running = True
def _sigterm(*_): 
    global running; running = False
signal.signal(signal.SIGTERM, _sigterm)
signal.signal(signal.SIGINT, _sigterm)

def chrony_waitsync(timeout=120):
    # returns True if synced within timeout
    try:
        return subprocess.run(["chronyc","waitsync",str(timeout)], check=False).returncode == 0
    except Exception:
        return False

def pps_wait_assert(dev="/dev/pps0", pulses=1, timeout=10):
    # Uses ppstest to wait for 1 or more PPS asserts.
    # Returns last UTC time when assert observed (float seconds).
    cmd = ["ppstest", dev]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + timeout
    last_ts = None
    count = 0
    pat = re.compile(r"assert .* time stamp:\s+(\d+)\.(\d+)")
    try:
        while time.time() < deadline:
            line = p.stdout.readline()
            if not line:
                time.sleep(0.01); continue
            m = pat.search(line)
            if m:
                sec = int(m.group(1)); nsec = int(m.group(2))
                last_ts = sec + nsec/1e9
                count += 1
                if count >= pulses: break
    finally:
        try: p.kill()
        except Exception: pass
    return last_ts

def sleep_to_next_full_minute_utc():
    now = datetime.now(timezone.utc)
    secs = now.second + now.microsecond/1e6
    time.sleep(60 - secs)

def is_within_night_local():
    now_local = datetime.now(LOCAL_TZ).time()
    # window 22:00–06:00 (crosses midnight)
    return (now_local >= datetime(2000,1,1,22,0).time()) or (now_local < datetime(2000,1,1,6,0).time())

def ensure_dirs(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def record_once():
    # Filename by UTC start time
    utc_start = datetime.now(timezone.utc)
    stamp = utc_start.strftime("%Y%m%dT%H%M%SZ")
    outwav = BASE_DIR / f"NFC_{stamp}.wav"
    meta = BASE_DIR / f"NFC_{stamp}.json"
    # Start arecord exactly on the next PPS to reduce start jitter
    # Wait for a PPS edge, then launch immediately.
    pps_wait_assert(pulses=1, timeout=5)

    arec = [
        "arecord", "-D", AUDIO_DEVICE,
        "-f", f"S{BITS}_LE",
        "-c", str(CHANNELS),
        "-r", str(RATE),
        "-d", str(REC_SEC),
        str(outwav)
    ]
    start_monotonic = time.monotonic()
    start_utc = datetime.now(timezone.utc)
    proc = subprocess.Popen(arec)
    rc = proc.wait()
    end_utc = datetime.now(timezone.utc)

    meta_dict = {
        "file": str(outwav.name),
        "utc_start": start_utc.isoformat().replace("+00:00","Z"),
        "utc_end": end_utc.isoformat().replace("+00:00","Z"),
        "sample_rate_hz": RATE,
        "bits": BITS,
        "channels": CHANNELS,
        "duration_s": REC_SEC,
        "arecord_rc": rc
    }
    with open(meta, "w") as f:
        json.dump(meta_dict, f, indent=2)

def main():
    ensure_dirs(BASE_DIR)
    chrony_ok = chrony_waitsync(120)
    if not chrony_ok:
        print("WARN: chrony not synced; continuing anyway", file=sys.stderr)

    # Align to next PPS and the next full UTC minute
    pps_wait_assert(pulses=1, timeout=10)
    sleep_to_next_full_minute_utc()

    while running:
        if is_within_night_local():
            record_once()
            # 5 s pause between segments (keeps cadence 59:55 / 5)
            for _ in range(PAUSE_SEC):
                if not running: break
                time.sleep(1)
        else:
            # Sleep to next minute when outside window
            sleep_to_next_full_minute_utc()
            time.sleep(1)

if __name__ == "__main__":
    main()
