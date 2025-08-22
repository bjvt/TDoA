import sounddevice as sd
import soundfile as sf
from datetime import datetime

duration = 60  # seconds
samplerate = 48000
filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.wav")

print("Recording...")
audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
sd.wait()
sf.write(filename, audio, samplerate)
print(f"Saved: {filename}")
