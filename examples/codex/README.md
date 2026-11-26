# Codex hook adapter

Review, trust, and install hooks yourself. This example is inert and does not
activate anything here. Install the package first and ensure
`agent-voice-notifier` is on the hook process's PATH.

Review [hooks.json](hooks.json), then merge the desired entries into the target
project's `.codex/hooks.json` following the
[official hook documentation](https://learn.chatgpt.com/docs/hooks).
Use the adapter's trust flow; do not overwrite existing configuration blindly.
Only install entries supported by your version. The command receives JSON on
stdin and runs in the session working directory. Output defaults to `out/` there;
choose an appropriate writable output location if you customize the command.

This adapter handles Stop, PermissionRequest, failed PostModelRequest, and a
pytest PostToolUse output heuristic. The tested PostToolUse payload has no
reliable exit-code field: silent nonzero exits are missed. Completion does not
mean tests passed. See the root README for all mappings and privacy behavior.
