# agent-voice-notifier

[![CI](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/codeql.yml/badge.svg)](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/codeql.yml)
[![gitleaks](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/sunnydachs/agent-voice-notifier/actions/workflows/gitleaks.yml)

[日本語](README.ja.md)

Local Japanese voice notifications for coding agents, using a separately
installed VOICEVOX engine and Zundamon Normal. Python 3.11+, standard-library-only
runtime. Supported hook adapters: Codex and Claude Code.

**VOICEVOX:ずんだもん** — unofficial project. No engine, voice models, character
art, or generated audio is bundled. Read [third-party notices](THIRD_PARTY_NOTICES.md)
and the [audio usage terms](https://zunko.jp/con_ongen_kiyaku.html).
Keep this visible credit with applications or media using generated audio.
The package code is [MIT licensed](LICENSE); third-party rights are separate.

## Install and try

Install [VOICEVOX](https://voicevox.hiroshiba.jp/) separately and start its engine
with Zundamon available. Install this package in a Python environment whose
console scripts are on PATH:

```sh
python -m pip install .
agent-voice-notifier --version
agent-voice-notifier --event complete
agent-voice-notifier --event approval --no-play
agent-voice-notifier --demo --output-dir out
```

`--event` accepts `complete`, `approval`, and `error`. Completion means the turn
finished; it does not claim that tests passed. Approval asks the listener to
check the screen. No arguments also generate the demo: three WAV files and a
`manifest.json`, without playback. Demo generation requires the engine;
`--no-play` skips playback, not synthesis.

The default engine URL is `http://127.0.0.1:50021`; override it with `--base-url`.
Only send requests to an engine you trust. The default output directory is
`out/` relative to the process working directory; `--output-dir` overrides it.

Playback supports native Windows and WSL with Windows PowerShell available.
WSL uses `wslpath -w`; PowerShell's `System.Media.SoundPlayer` plays synchronously.
Other platforms can generate audio with `--no-play` or `--demo` but have no
built-in player. No playback dependencies are installed by this package.

## Optional hook adapters

The [Codex example](examples/codex/README.md) and
[Claude Code example](examples/claude-code/README.md) invoke
`agent-voice-notifier --hook` and receive one JSON object on stdin.
Users must review, trust, and install hooks themselves. Installing the Python
package does not install or activate hooks. Examples are inert files in
`examples/`; no hooks are activated in this repository.

| Input | Notification |
| --- | --- |
| `Stop` without background tasks or session crons | complete |
| `PermissionRequest`, or `Notification` with `permission_prompt` | approval |
| `StopFailure`, or failed `PostModelRequest` | error |
| `PostToolUseFailure` for Bash/PowerShell running pytest | error |
| Bash `PostToolUse` running pytest with recognizable failure output | error |

These mappings cover supported adapter payloads; event availability depends on
the adapter/version. Idle prompts and unrelated tool failures are ignored.
Ignored hooks exit successfully and silently before contacting the engine or
creating files. Handled hooks also produce no stdout. Hook runtime failures
return success with a generic stderr diagnostic, so notifications do not block
the agent; manual command failures return status 1. Invalid CLI options use
argparse's status 2.

**Codex limitation:** `PostToolUse` has no reliable exit-code field in the tested
payload. Pytest error detection is an output heuristic (`FAILED`, `ERROR`, or a
nonzero `N failed` summary). Silent nonzero exits are missed; unusual output
can also produce false positives or misses. This is not a test-status monitor.

## Cache and privacy

Speech uses only a fixed event message and a short project basename from the
hook payload's `cwd`. Both Windows and POSIX separators work. Characters outside
ASCII letters, digits, `_`, and `-` become hyphens; names are limited to 32
characters. Missing or empty names fall back to `coding-agent`. Manual events
use that fallback. A basename may itself be sensitive: it is spoken and sent
to the configured engine. No transcript is read.

The client resolves Zundamon Normal through `GET /speakers`, then uses
`POST /audio_query` and `POST /synthesis` with query parameters. A SHA-256 key of
engine URL, speaker ID, and speech text names each cached WAV. Valid cached
PCM audio is reused; corrupt entries are regenerated. Audio is validated before
atomic cache replacement and before playback. Replacing an engine/voice at the
same URL with the same ID requires clearing the cache manually.

`events.jsonl` records UTC receipt and playback timestamps, event, allowlisted
hook event, WAV basename, duration, cache status, and playback status. Skipped
playback has null timestamps; failed playback has a start time and no finish
time. Synthesis failures emit no event record. Raw payloads, speech text,
project names, session IDs, model/provider fields, commands, cwd, and transcript
paths are not logged. Generated outputs stay local; remove the output directory
to clear them. Output files and caches are excluded from Git.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `python -m pytest -q` after installing
`.[test]`. Unit tests block real network access and playback, and use synthetic
payloads. CI covers Python 3.11–3.14 and a basic gitleaks scan. There is no release
pipeline.
