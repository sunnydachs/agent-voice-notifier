# Contributing

Use Python 3.11 or newer. Install development tools in an isolated environment:

```sh
python -m venv .venv
python -m pip install -e '.[test]'
python -m pytest -q
```

Run the last two commands with the environment's Python after activating it.
Tests must stay offline and block real network access and playback. Keep the
runtime standard-library-only. Include regression tests for behavior changes.
CI installs dependencies before running the offline tests on Python 3.11–3.14.

Use synthetic hook payloads. Do not contribute real event logs, audio, personal
paths, session identifiers, transcripts, credentials, or account information.
Do not activate hooks as part of development. Preserve quiet ignored events
and the documented limits of pytest failure detection.

Contributions are accepted under the MIT license in LICENSE. Audio and
character rights remain separate; see THIRD_PARTY_NOTICES.md.
