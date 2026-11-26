# Claude Code hook adapter

Review, trust, and install hooks yourself. This example is inert and does not
activate anything here. Install the package first and ensure
`agent-voice-notifier` is on the hook process's PATH.

Review [settings.json](settings.json), then merge the desired entries into the
target project's `.claude/settings.json` following the
[official hook reference](https://code.claude.com/docs/en/hooks).
Use the adapter's review flow; do not overwrite existing configuration blindly.
Only install entries supported by your version. Use the permission
`Notification` entry for approval prompts. The command receives JSON on stdin.
Output defaults to `out/` in its working directory; choose a writable location
when customizing it.

This adapter handles Stop, permission prompts, StopFailure, and pytest failures
from Bash/PowerShell PostToolUseFailure. Unrelated failures and idle prompts are
ignored. See the root README for all mappings and privacy behavior.
