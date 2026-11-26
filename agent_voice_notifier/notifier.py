"""Validated content-addressed audio cache and minimal event records."""

import hashlib
import json
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

from .audio import play_wav, synthesize, wav_duration
from .hooks import HOOK_EVENTS, message


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def notify_event(event, speaker_id, base_url, output_dir, play=False, payload=None):
    received_at = timestamp()
    text = message(event, payload)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    identity = json.dumps([base_url.rstrip('/'), speaker_id, text], ensure_ascii=False)
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    path = output_dir / f"{key}.wav"
    cache = "hit"
    try:
        duration = wav_duration(path)
    except (OSError, ValueError, EOFError, wave.Error):
        cache = "miss"
        with tempfile.NamedTemporaryFile(dir=output_dir, suffix=".wav", delete=False) as wav:
            temporary = Path(wav.name)
        try:
            temporary.write_bytes(synthesize(text, speaker_id, base_url))
            duration = wav_duration(temporary)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    hook = (payload or {}).get("hook_event_name")
    record = {
        "received_at": received_at,
        "event": event,
        "hook_event": hook if hook in HOOK_EVENTS else "manual",
        "file": path.name,
        "duration_sec": round(duration, 3),
        "cache": cache,
        "playback": "skipped",
        "playback_started_at": None,
        "playback_finished_at": None,
    }
    try:
        if play:
            record["playback"] = "failed"
            record["playback_started_at"] = timestamp()
            play_wav(path)
            record["playback_finished_at"] = timestamp()
            record["playback"] = "played"
    finally:
        with (output_dir / "events.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
