import io
import json
import wave
from unittest.mock import Mock
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from agent_voice_notifier import audio


def wav_bytes(frames=800):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b'\0\0' * frames)
    return buffer.getvalue()


def test_dynamic_speaker_resolution():
    assert audio.find_speaker_id([
        {'name': 'other', 'styles': [{'name': 'ノーマル', 'id': 1}]},
        {'name': 'ずんだもん', 'styles': [{'name': 'other', 'id': 2}, {'name': 'ノーマル', 'id': 37}]},
    ]) == 37
    with pytest.raises(ValueError):
        audio.find_speaker_id([])


def test_post_query_protocol(monkeypatch):
    calls = []
    def request(req, timeout):
        calls.append(req)
        assert timeout == 60
        assert req.get_method() == 'POST'
        assert req.get_header('Content-type') == 'application/json'
        parsed = urlparse(req.full_url)
        if parsed.path == '/audio_query':
            assert parse_qs(parsed.query) == {'text': ['通知なのだ'], 'speaker': ['37']}
            assert req.data == b'{}'
            return io.BytesIO(b'{"query": true}')
        assert parsed.path == '/synthesis'
        assert parse_qs(parsed.query) == {'speaker': ['37']}
        assert json.loads(req.data) == {'query': True}
        return io.BytesIO(wav_bytes())
    monkeypatch.setattr(audio.urllib.request, 'urlopen', request)
    assert audio.synthesize('通知なのだ', 37, 'http://localhost:50021/') == wav_bytes()
    assert len(calls) == 2


@pytest.mark.parametrize('data,valid', [(wav_bytes(), True), (b'bad', False),
                                       (wav_bytes(0), False), (wav_bytes()[:-2], False)])
def test_wav_validation_and_duration(tmp_path, data, valid):
    path = tmp_path / 'sample.wav'
    path.write_bytes(data)
    if valid:
        assert audio.wav_duration(path) == 0.1
    else:
        with pytest.raises((ValueError, wave.Error, EOFError)):
            audio.wav_duration(path)


@pytest.mark.parametrize('native', [False, True])
def test_playback_windows_and_wsl(monkeypatch, tmp_path, native):
    run = Mock()
    convert = Mock(return_value="C:\\audio\\it's.wav\n")
    monkeypatch.setattr(audio.subprocess, 'check_output', convert)
    monkeypatch.setattr(audio.subprocess, 'run', run)
    # Replace only the module's os reference, avoiding changes to pathlib internals.
    monkeypatch.setattr(audio, 'os', SimpleNamespace(name='nt' if native else 'posix'))
    path = tmp_path / "it's.wav"
    audio.play_wav(path)
    if native:
        convert.assert_not_called()
    else:
        assert convert.call_args.args[0] == ['wslpath', '-w', str(path.resolve())]
    command = run.call_args.args[0]
    assert command[:4] == ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command']
    assert 'System.Media.SoundPlayer' in command[-1]
    assert "it''s.wav" in command[-1]
    assert run.call_args.kwargs['check'] is True
