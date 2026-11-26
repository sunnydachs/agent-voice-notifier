"""VOICEVOX HTTP protocol, PCM WAV validation, and Windows/WSL playback."""

import os
import subprocess
import urllib.request
import wave
from pathlib import Path
from urllib.parse import urlencode


def find_speaker_id(speakers, name="ずんだもん", style="ノーマル"):
    for speaker in speakers:
        if speaker.get("name") == name:
            for item in speaker.get("styles", []):
                if item.get("name") == style:
                    return int(item["id"])
    raise ValueError("Requested VOICEVOX speaker/style was not found")


def synthesize(text, speaker_id, base_url):
    def post(endpoint, params, body):
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}{endpoint}?{urlencode(params)}",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()

    query = post("/audio_query", {"text": text, "speaker": speaker_id}, b"{}")
    return post("/synthesis", {"speaker": speaker_id}, query)


def wav_duration(path):
    """Reject empty, malformed, or truncated PCM audio before playback/caching."""
    with wave.open(str(path), "rb") as wav:
        frames, rate = wav.getnframes(), wav.getframerate()
        if frames <= 0 or rate <= 0 or wav.getcomptype() != "NONE":
            raise ValueError("Invalid PCM WAV")
        expected = frames * wav.getnchannels() * wav.getsampwidth()
        if len(wav.readframes(frames)) != expected:
            raise ValueError("Truncated PCM WAV")
        return frames / rate


def play_wav(path):
    path = str(Path(path).resolve())
    if os.name != "nt":
        path = subprocess.check_output(["wslpath", "-w", path], text=True, timeout=10).strip()
    quoted = path.replace("'", "''")
    script = f"(New-Object System.Media.SoundPlayer '{quoted}').PlaySync()"
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True, capture_output=True, timeout=30,
    )
