import nfc
import subprocess
from datetime import datetime

def on_connect(tag):
    tag_id = str(tag.identifier.hex())
    log_entry = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S - Tag ID: {tag_id}\n")
    with open("nfc_log.txt", "a") as log:
        log.write(log_entry)
    print("NFC tag detected! Starting recording...")
    subprocess.run(["python3", "record.py"])
    return True

clf = nfc.ContactlessFrontend('usb')
while True:
    clf.connect(rdwr={'on-connect': on_connect})
