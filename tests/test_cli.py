import io
import json
import sys
from unittest.mock import Mock

import pytest

from agent_voice_notifier import __version__, cli, notifier
from test_audio import wav_bytes


@pytest.fixture
def engine(monkeypatch):
    speakers = [{'name': 'ずんだもん', 'styles': [{'id': 37, 'name': 'ノーマル'}]}]
    def fetch(url, timeout):
        assert url == 'http://localhost:50021/speakers'
        assert timeout == 10
        return io.BytesIO(json.dumps(speakers).encode())
    monkeypatch.setattr(cli.urllib.request, 'urlopen', fetch)
    monkeypatch.setattr(notifier, 'synthesize', Mock(return_value=wav_bytes()))
    play = Mock()
    monkeypatch.setattr(notifier, 'play_wav', play)
    return play


def test_version(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(['--version'])
    assert error.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.parametrize('no_play', [False, True])
def test_event_cli(engine, tmp_path, capsys, no_play):
    args = ['--event', 'approval', '--base-url', 'http://localhost:50021', '--output-dir', str(tmp_path)]
    assert cli.main(args + (['--no-play'] if no_play else [])) == 0
    record = json.loads(capsys.readouterr().out)
    assert record['event'] == 'approval'
    assert record['playback'] == ('skipped' if no_play else 'played')
    assert engine.call_count == (0 if no_play else 1)


@pytest.mark.parametrize('explicit', [False, True])
def test_demo_generates_manifest_without_playback(engine, tmp_path, capsys, explicit):
    assert cli.main(['--base-url', 'http://localhost:50021', '--output-dir', str(tmp_path)] +
                    (['--demo'] if explicit else [])) == 0
    manifest = json.loads((tmp_path / 'manifest.json').read_text())
    assert json.loads(capsys.readouterr().out) == manifest
    assert manifest['speaker_id'] == 37
    assert [item['event'] for item in manifest['notifications']] == ['complete', 'approval', 'error']
    assert len(list(tmp_path.glob('*.wav'))) == 3
    engine.assert_not_called()


def test_hook_cli_quiet_success(engine, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{"hook_event_name":"Stop"}'))
    assert cli.main(['--hook', '--no-play', '--base-url', 'http://localhost:50021',
                     '--output-dir', str(tmp_path)]) == 0
    assert capsys.readouterr() == ('', '')
    assert json.loads((tmp_path / 'events.jsonl').read_text())['event'] == 'complete'
    engine.assert_not_called()


def test_ignored_hook_has_no_side_effects(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{"hook_event_name":"Notification","notification_type":"idle_prompt"}'))
    fetch = Mock(side_effect=AssertionError('Must not contact engine'))
    monkeypatch.setattr(cli.urllib.request, 'urlopen', fetch)
    output = tmp_path / 'out'
    assert cli.main(['--hook', '--output-dir', str(output)]) == 0
    fetch.assert_not_called()
    assert not output.exists()
    assert capsys.readouterr() == ('', '')


@pytest.mark.parametrize('data', ['not json', '[]', 'null'])
def test_invalid_hook_input_is_nonblocking_and_redacted(monkeypatch, capsys, data):
    monkeypatch.setattr(sys, 'stdin', io.StringIO(data))
    assert cli.main(['--hook']) == 0
    capture = capsys.readouterr()
    assert capture.out == ''
    assert 'Voice notification failed' in capture.err


@pytest.mark.parametrize('hook', [False, True])
def test_engine_failure_exit_status_and_redaction(monkeypatch, capsys, hook):
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{"hook_event_name":"Stop"}'))
    monkeypatch.setattr(cli.urllib.request, 'urlopen', Mock(side_effect=OSError('private-value')))
    assert cli.main(['--hook'] if hook else ['--event', 'error']) == (0 if hook else 1)
    capture = capsys.readouterr()
    assert capture.out == '' and 'private-value' not in capture.err
    assert 'Voice notification failed' in capture.err


def test_example_configs_are_portable():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for adapter, filename in [('codex', 'hooks.json'), ('claude-code', 'settings.json')]:
        config = json.loads((root / 'examples' / adapter / filename).read_text())
        required = {
            'codex': {'Stop', 'PermissionRequest', 'PostToolUse'},
            'claude-code': {'Stop', 'Notification', 'StopFailure', 'PostToolUseFailure'},
        }
        assert required[adapter] <= set(config['hooks'])
        if adapter == 'claude-code':
            assert 'PermissionRequest' not in config['hooks']
        for groups in config['hooks'].values():
            for group in groups:
                for hook in group['hooks']:
                    assert hook['command'] == 'agent-voice-notifier --hook'
