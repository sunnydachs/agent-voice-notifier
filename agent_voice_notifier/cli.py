"""Console interface; hook mode never writes control output to stdout."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from . import __version__
from .audio import find_speaker_id
from .hooks import EVENTS, map_hook
from .notifier import notify_event


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local VOICEVOX agent notifications")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--base-url", default="http://127.0.0.1:50021")
    parser.add_argument("--output-dir", type=Path, default=Path("out"))
    parser.add_argument("--no-play", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--event", choices=EVENTS)
    action.add_argument("--hook", action="store_true")
    action.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = json.load(sys.stdin) if args.hook else None
        event = map_hook(payload) if args.hook else args.event
        if args.hook and event is None:
            return 0
        with urllib.request.urlopen(f"{args.base_url.rstrip('/')}/speakers", timeout=10) as response:
            speaker_id = find_speaker_id(json.load(response))
        if event:
            record = notify_event(event, speaker_id, args.base_url, args.output_dir,
                                  play=not args.no_play, payload=payload)
            if not args.hook:
                print(json.dumps(record, ensure_ascii=False))
        else:
            records = [notify_event(item, speaker_id, args.base_url, args.output_dir) for item in EVENTS]
            manifest = {"speaker": "ずんだもん", "style": "ノーマル",
                        "speaker_id": speaker_id, "notifications": records}
            (args.output_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(manifest, ensure_ascii=False))
        return 0
    except Exception:
        # Exception strings can contain private paths or hook content.
        print("Voice notification failed; check engine, output directory, and playback setup.", file=sys.stderr)
        return 0 if args.hook else 1
