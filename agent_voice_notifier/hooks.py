"""Mappings for supported Codex and Claude Code hook payloads."""

import json
import re

EVENTS = ("complete", "approval", "error")
HOOK_EVENTS = {
    "Stop", "Notification", "PermissionRequest", "StopFailure",
    "PostModelRequest", "PostToolUseFailure", "PostToolUse",
}
MESSAGES = {
    "complete": "作業が終わったのだ。結果は画面で確認してほしいのだ。",
    "approval": "承認待ちなのだ。画面確認が必要なのだ。",
    "error": "エラーが出たのだ。画面で内容を確認してほしいのだ。",
}


def project_name(payload):
    """Return at most 32 safe ASCII characters from a POSIX or Windows basename."""
    cwd = payload.get("cwd")
    if not isinstance(cwd, str):
        return "coding-agent"
    basename = cwd.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", basename).strip("-_")[:32]
    return name or "coding-agent"


def message(event, payload=None):
    return f"{project_name(payload or {})}、{MESSAGES[event]}"


def map_hook(payload):
    """Map a hook to an event; unrelated events return None without side effects."""
    if not isinstance(payload, dict):
        raise ValueError("Hook input must be a JSON object")
    name = payload.get("hook_event_name")
    if name == "Stop":
        return None if payload.get("background_tasks") or payload.get("session_crons") else "complete"
    if name == "PermissionRequest" or (
        name == "Notification" and payload.get("notification_type") == "permission_prompt"
    ):
        return "approval"
    if name == "StopFailure" or (name == "PostModelRequest" and payload.get("status") == "failed"):
        return "error"
    tool_input = payload.get("tool_input")
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not re.search(r"\bpytest\b", command):
        return None
    if name == "PostToolUseFailure" and payload.get("tool_name") in {"Bash", "PowerShell"}:
        return "error"
    if name == "PostToolUse" and payload.get("tool_name") == "Bash":
        response = payload.get("tool_response")
        output = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        # shortcut: tested Codex payloads lack a reliable exit code; silent failures are missed.
        if re.search(r"(?m)^(FAILED|ERROR)\b|\b[1-9]\d* failed\b", output):
            return "error"
    return None
