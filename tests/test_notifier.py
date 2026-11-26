import json
import subprocess
from datetime import datetime
from unittest.mock import Mock

import pytest

from agent_voice_notifier import notifier
from test_audio import wav_bytes


def test_cache_log_privacy_and_playback(monkeypatch, tmp_path):
    synth = Mock(return_value=wav_bytes())
    play = Mock()
    monkeypatch.setattr(notifier, 'synthesize', synth)
    monkeypatch.setattr(notifier, 'play_wav', play)
    payload = {'hook_event_name': 'Stop', 'cwd': '/workspace/sample-project',
               'model': 'private-value', 'provider': 'private-value',
               'command': 'private-value', 'transcript_path': 'private-value',
               'session_id': 'private-value', 'turn_id': 'private-value'}
    first = notifier.notify_event('complete', 37, 'http://localhost', tmp_path, play=True, payload=payload)
    second = notifier.notify_event('complete', 37, 'http://localhost', tmp_path, payload=payload)
    assert synth.call_count == 1
    assert synth.call_args.args[0].startswith('sample-project、')
    play.assert_called_once_with(tmp_path / first['file'])
    assert first['cache'] == 'miss' and second['cache'] == 'hit'
    assert len(first['file']) == 68
    assert first['playback'] == 'played' and second['playback'] == 'skipped'
    assert second['playback_started_at'] is None and second['playback_finished_at'] is None
    assert datetime.fromisoformat(first['received_at']) <= datetime.fromisoformat(first['playback_started_at'])
    assert datetime.fromisoformat(first['playback_started_at']) <= datetime.fromisoformat(first['playback_finished_at'])
    log = (tmp_path / 'events.jsonl').read_text()
    assert [json.loads(line) for line in log.splitlines()] == [first, second]
    assert set(first) == {'received_at', 'event', 'hook_event', 'file', 'duration_sec',
                          'cache', 'playback', 'playback_started_at', 'playback_finished_at'}
    assert first['duration_sec'] == 0.1 and first['hook_event'] == 'Stop'
    for sensitive in ['private-value', '/workspace', 'sample-project', 'model', 'provider',
                      'command', 'cwd', 'transcript_path', 'session_id', 'turn_id']:
        assert sensitive not in log


def test_cache_identity_and_corrupt_cache_recovery(monkeypatch, tmp_path):
    synth = Mock(return_value=wav_bytes())
    monkeypatch.setattr(notifier, 'synthesize', synth)
    def notify(**kwargs):
        return notifier.notify_event(output_dir=tmp_path, **kwargs)
    base = dict(event='complete', speaker_id=37, base_url='http://localhost')
    original = notify(**base)
    (tmp_path / original['file']).write_bytes(b'corrupt')
    assert notify(**base)['cache'] == 'miss'
    variants = [{**base, 'event': 'error'}, {**base, 'speaker_id': 38},
                {**base, 'base_url': 'http://localhost:50021'},
                {**base, 'payload': {'cwd': '/workspace/other-project'}}]
    files = {original['file'], *(notify(**item)['file'] for item in variants)}
    assert len(files) == 5
    assert synth.call_count == 6


def test_invalid_synthesis_never_cached_or_played(monkeypatch, tmp_path):
    monkeypatch.setattr(notifier, 'synthesize', Mock(return_value=b'bad'))
    play = Mock()
    monkeypatch.setattr(notifier, 'play_wav', play)
    with pytest.raises(EOFError):
        notifier.notify_event('error', 37, 'http://localhost', tmp_path, play=True)
    assert list(tmp_path.iterdir()) == []
    play.assert_not_called()


def test_playback_failure_is_logged_without_private_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(notifier, 'synthesize', Mock(return_value=wav_bytes()))
    monkeypatch.setattr(notifier, 'play_wav', Mock(side_effect=subprocess.TimeoutExpired('private-value', 30)))
    with pytest.raises(subprocess.TimeoutExpired):
        notifier.notify_event('error', 37, 'http://localhost', tmp_path, play=True)
    content = (tmp_path / 'events.jsonl').read_text()
    record = json.loads(content)
    assert record['playback'] == 'failed'
    assert record['playback_started_at'] is not None
    assert record['playback_finished_at'] is None
    assert 'private-value' not in content
