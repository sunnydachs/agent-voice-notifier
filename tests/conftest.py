"""Tests must never reach an engine or start external programs."""
import socket
import subprocess
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Network access and playback are forbidden in unit tests')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'check_output', forbidden)
