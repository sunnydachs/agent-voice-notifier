import pytest

from agent_voice_notifier.hooks import EVENTS, map_hook, message, project_name


@pytest.mark.parametrize('payload,event', [
    ({'hook_event_name': 'Stop'}, 'complete'),
    ({'hook_event_name': 'PermissionRequest'}, 'approval'),
    ({'hook_event_name': 'PostModelRequest', 'status': 'failed'}, 'error'),
    ({'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
      'tool_input': {'command': 'python -m pytest -q'},
      'tool_response': {'stdout': '1 failed, 2 passed'}}, 'error'),
])
def test_codex_mappings(payload, event):
    assert map_hook(payload) == event


@pytest.mark.parametrize('payload,event', [
    ({'hook_event_name': 'Stop'}, 'complete'),
    ({'hook_event_name': 'Notification', 'notification_type': 'permission_prompt'}, 'approval'),
    ({'hook_event_name': 'PermissionRequest'}, 'approval'),
    ({'hook_event_name': 'StopFailure'}, 'error'),
    ({'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash',
      'tool_input': {'command': 'pytest tests/'}}, 'error'),
    ({'hook_event_name': 'PostToolUseFailure', 'tool_name': 'PowerShell',
      'tool_input': {'command': 'python -m pytest'}}, 'error'),
])
def test_claude_code_mappings(payload, event):
    assert map_hook(payload) == event


@pytest.mark.parametrize('output', ['FAILED tests/test_example.py - AssertionError',
                                      'ERROR: file or directory not found', '3 failed, 1 passed'])
def test_pytest_output_heuristic(output):
    assert map_hook({'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
                     'tool_input': {'command': 'pytest'}, 'tool_response': output}) == 'error'


@pytest.mark.parametrize('output', ['', 'probe-ok\n', '12 passed', {'stdout': ''}])
def test_codex_silent_nonzero_exits_are_missed(output):
    # No reliable exit-code field in the tested payload: only output is inspected.
    assert map_hook({'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
                     'tool_input': {'command': 'pytest'}, 'tool_response': output}) is None


@pytest.mark.parametrize('payload', [
    {}, {'hook_event_name': 'Stop', 'background_tasks': [True]},
    {'hook_event_name': 'Stop', 'session_crons': [True]},
    {'hook_event_name': 'Notification', 'notification_type': 'idle_prompt'},
    {'hook_event_name': 'PostModelRequest', 'status': 'completed'},
    {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash', 'tool_input': {'command': 'lint'}},
    {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Write', 'tool_input': {'command': 'pytest'}},
    {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash', 'tool_input': None},
    {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 1}},
])
def test_ignored_hooks(payload):
    assert map_hook(payload) is None


@pytest.mark.parametrize('cwd,expected', [
    ('/workspace/sample-project/', 'sample-project'),
    ('C:\\workspace\\sample-project', 'sample-project'),
    ('/workspace/a b;$(x)', 'a-b-x'),
    ('/workspace/' + 'x' * 60, 'x' * 32),
    ('/', 'coding-agent'), (None, 'coding-agent'), ('/workspace/日本語', 'coding-agent'),
])
def test_safe_project_basename(cwd, expected):
    assert project_name({'cwd': cwd}) == expected


def test_messages_are_general_and_do_not_claim_tests_passed():
    assert set(EVENTS) == {'complete', 'approval', 'error'}
    assert '作業が終わった' in message('complete')
    assert 'テスト成功' not in message('complete')
    assert '承認待ち' in message('approval') and '画面確認' in message('approval')
    assert 'エラー' in message('error')
    assert message('complete').startswith('coding-agent、')


@pytest.mark.parametrize('payload', [[], None, 'Stop'])
def test_invalid_hook_shape(payload):
    with pytest.raises(ValueError):
        map_hook(payload)
